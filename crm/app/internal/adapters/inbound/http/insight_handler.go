// Package http — Insight handler: GET /api/parties/{id}/insight
//
// Surfaces wh_customer_insight + wh_action_queue + recent wh_order_hdr for a party
// by resolving the sapo_customer identity and querying the cache (ATTACHed read-only).
//
// Graceful-empty contract: when cache.db has no wh_* tables yet (before the first
// Python sync run) the endpoint returns {"insight": null} with HTTP 200 — not 500.
// The caller can distinguish "no data yet" from "party not found" via HTTP status.
package http

import (
	"context"
	"log"
	"net/http"
	"strconv"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── port interfaces (dependency-inversion; handler owns no concrete types) ──

// IdentityReader resolves a party's Sapo customer_id from crm_party_identity.
type IdentityReader interface {
	ListIdentities(ctx context.Context, partyID string) ([]domain.PartyIdentity, error)
}

// InsightReader fetches the cached insight from cache.db.
type InsightReader interface {
	GetCustomerInsight(ctx context.Context, customerID int64) (*domain.CacheInsight, error)
}

// ─── handler ─────────────────────────────────────────────────────────────────

// InsightHandler serves GET /api/parties/{id}/insight.
type InsightHandler struct {
	identities IdentityReader
	cache      InsightReader
}

// NewInsightHandler constructs the handler.
func NewInsightHandler(identities IdentityReader, cache InsightReader) *InsightHandler {
	return &InsightHandler{identities: identities, cache: cache}
}

// RegisterRoutes mounts insight routes on the given chi router.
func (h *InsightHandler) RegisterRoutes(r chi.Router) {
	r.Get("/api/parties/{id}/insight", h.getInsight)
}

// GET /api/parties/{id}/insight
// Returns {"insight": <CacheInsight>} or {"insight": null} when cache is empty.
// Returns 404 when the party has no sapo_customer identity.
func (h *InsightHandler) getInsight(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")

	// Resolve sapo_customer identity → customer_id.
	customerID, err := h.resolveSapoCustomerID(r.Context(), partyID)
	if err != nil {
		log.Printf("insight: resolve identity %s: %v", partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to resolve identity")
		return
	}
	if customerID == 0 {
		writeError(w, http.StatusNotFound, "no sapo_customer identity for this party")
		return
	}

	insight, err := h.cache.GetCustomerInsight(r.Context(), customerID)
	if err != nil {
		log.Printf("insight: get customer insight party=%s cid=%d: %v", partyID, customerID, err)
		writeError(w, http.StatusInternalServerError, "failed to get insight")
		return
	}

	// insight == nil means cache is empty — return null gracefully (HTTP 200).
	writeJSON(w, http.StatusOK, map[string]any{"insight": insight})
}

// resolveSapoCustomerID returns the int64 Sapo customer_id from the party's identities.
// Returns 0 when no sapo_customer identity exists.
func (h *InsightHandler) resolveSapoCustomerID(ctx context.Context, partyID string) (int64, error) {
	identities, err := h.identities.ListIdentities(ctx, partyID)
	if err != nil {
		return 0, err
	}
	for _, id := range identities {
		if id.IdentityType == "sapo_customer" {
			n, err := strconv.ParseInt(id.IdentityValue, 10, 64)
			if err != nil {
				continue
			}
			return n, nil
		}
	}
	return 0, nil
}


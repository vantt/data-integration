// Package http — Activity HTTP handlers.
// Auth: DEFERRED — LAN-trust only (per plan). No auth middleware here.
package http

import (
	"context"
	"encoding/json"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ActivityLister is the read interface needed by the activity handler.
type ActivityLister interface {
	ListTimeline(ctx context.Context, partyID string) ([]domain.Activity, error)
}

// ActivityLogger is the write interface needed by the activity handler.
type ActivityLogger interface {
	LogActivity(ctx context.Context, a *domain.Activity) error
}

// ActivityHandler wires activity endpoints.
type ActivityHandler struct {
	lister ActivityLister
	logger ActivityLogger
}

// NewActivityHandler constructs the handler.
func NewActivityHandler(lister ActivityLister, logger ActivityLogger) *ActivityHandler {
	return &ActivityHandler{lister: lister, logger: logger}
}

// RegisterRoutes mounts activity routes on the given chi router.
func (h *ActivityHandler) RegisterRoutes(r chi.Router) {
	r.Get("/api/parties/{id}/activities", h.listTimeline)
	r.Post("/api/parties/{id}/activities", h.logActivity)
}

// GET /api/parties/{id}/activities
func (h *ActivityHandler) listTimeline(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")
	acts, err := h.lister.ListTimeline(r.Context(), partyID)
	if err != nil {
		log.Printf("activity handler: list timeline %s: %v", partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to list activities")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"party_id": partyID, "activities": acts})
}

// POST /api/parties/{id}/activities
func (h *ActivityHandler) logActivity(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")

	var body struct {
		ActivityType     string  `json:"activity_type"`
		Direction        string  `json:"direction"`
		Channel          string  `json:"channel"`
		Subject          string  `json:"subject"`
		Body             string  `json:"body"`
		Outcome          string  `json:"outcome"`
		RelatedOrderCode string  `json:"related_order_code"`
		StaffUserID      *string `json:"staff_user_id"`
		OccurredAt       string  `json:"occurred_at"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	act := &domain.Activity{
		PartyID:          partyID,
		ActivityType:     body.ActivityType,
		Direction:        body.Direction,
		Channel:          body.Channel,
		Subject:          body.Subject,
		Body:             body.Body,
		Outcome:          body.Outcome,
		RelatedOrderCode: body.RelatedOrderCode,
		StaffUserID:      body.StaffUserID,
		OccurredAt:       body.OccurredAt,
	}
	if err := h.logger.LogActivity(r.Context(), act); err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("activity handler: log activity %s: %v", partyID, err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusCreated, act)
}

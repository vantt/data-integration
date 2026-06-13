// Package http — dedup HTTP handlers.
// Interface-based; no direct import of sqlite or application packages.
//
// Auth: DEFERRED — endpoints are LAN-trust only (per plan). No auth middleware added here.
package http

import (
	"context"
	"encoding/json"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// DedupQuerier is the minimal read interface the dedup list handler needs.
type DedupQuerier interface {
	ListCandidates(ctx context.Context, status string) ([]domain.DedupCandidate, error)
	GetCandidate(ctx context.Context, candidateID string) (*domain.DedupCandidate, error)
	UpdateCandidateStatus(ctx context.Context, candidateID, status string, reviewedBy *string) error
}

// DedupMerger is the minimal merge interface the merge handler needs.
type DedupMerger interface {
	Merge(ctx context.Context, survivingPartyID, mergedPartyID, reason string, mergedBy *string) (string, error)
}

// DedupHandler holds dependencies for all dedup HTTP handlers.
type DedupHandler struct {
	querier DedupQuerier
	merger  DedupMerger
}

// NewDedupHandler constructs a DedupHandler.
func NewDedupHandler(q DedupQuerier, m DedupMerger) *DedupHandler {
	return &DedupHandler{querier: q, merger: m}
}

// RegisterRoutes wires dedup endpoints onto a chi router.
func (h *DedupHandler) RegisterRoutes(r chi.Router) {
	r.Get("/api/dedup/candidates", h.listCandidates)
	r.Post("/api/dedup/merge", h.mergeCandidates)
	r.Post("/api/dedup/candidates/{id}/reject", h.rejectCandidate)
}

// listCandidates handles GET /api/dedup/candidates
// Optional query param: ?status=pending|merged|rejected (default: pending)
func (h *DedupHandler) listCandidates(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	if status == "" {
		status = "pending"
	}

	candidates, err := h.querier.ListCandidates(r.Context(), status)
	if err != nil {
		log.Printf("dedup: list candidates: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list candidates")
		return
	}
	if candidates == nil {
		candidates = []domain.DedupCandidate{}
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"status":     "ok",
		"count":      len(candidates),
		"candidates": candidates,
	})
}

type mergeRequest struct {
	SurvivingID string  `json:"surviving_id"`
	MergedID    string  `json:"merged_id"`
	Reason      string  `json:"reason"`
	MergedBy    *string `json:"merged_by,omitempty"`
}

// mergeCandidates handles POST /api/dedup/merge
func (h *DedupHandler) mergeCandidates(w http.ResponseWriter, r *http.Request) {
	var req mergeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.SurvivingID == "" || req.MergedID == "" {
		writeError(w, http.StatusBadRequest, "surviving_id and merged_id are required")
		return
	}

	mergeID, err := h.merger.Merge(r.Context(), req.SurvivingID, req.MergedID, req.Reason, req.MergedBy)
	if err != nil {
		log.Printf("dedup: merge %s→%s: %v", req.MergedID, req.SurvivingID, err)
		writeError(w, http.StatusInternalServerError, "merge failed")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"status":   "ok",
		"merge_id": mergeID,
	})
}

// rejectCandidate handles POST /api/dedup/candidates/{id}/reject
func (h *DedupHandler) rejectCandidate(w http.ResponseWriter, r *http.Request) {
	candidateID := chi.URLParam(r, "id")
	if candidateID == "" {
		writeError(w, http.StatusBadRequest, "candidate id required")
		return
	}

	c, err := h.querier.GetCandidate(r.Context(), candidateID)
	if err != nil {
		log.Printf("dedup: get candidate %s: %v", candidateID, err)
		writeError(w, http.StatusInternalServerError, "operation failed")
		return
	}
	if c == nil {
		writeError(w, http.StatusNotFound, "candidate not found")
		return
	}

	if err := h.querier.UpdateCandidateStatus(r.Context(), candidateID, "rejected", nil); err != nil {
		log.Printf("dedup: reject candidate %s: %v", candidateID, err)
		writeError(w, http.StatusInternalServerError, "operation failed")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "candidate_id": candidateID})
}

// writeJSON encodes v as JSON with the given status code.
func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

// writeError writes a JSON error response.
func writeError(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

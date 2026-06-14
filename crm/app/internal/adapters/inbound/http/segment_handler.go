// Package http — Segment HTTP handlers.
// Auth: DEFERRED — LAN-trust only (per plan).
package http

import (
	"context"
	"encoding/json"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// SegmentReader covers read operations for segments.
type SegmentReader interface {
	GetSegment(ctx context.Context, segmentID string) (*domain.Segment, error)
	ListSegments(ctx context.Context) ([]domain.Segment, error)
	ListMembers(ctx context.Context, segmentID string) ([]domain.SegmentMember, error)
}

// SegmentWriter covers create/update and manual member management.
type SegmentWriter interface {
	CreateSegment(ctx context.Context, seg *domain.Segment) error
	UpdateSegment(ctx context.Context, seg *domain.Segment) error
	AddMember(ctx context.Context, segmentID, partyID string) error
	RemoveMember(ctx context.Context, segmentID, partyID string) error
}

// SegmentRefresher triggers dynamic segment re-evaluation.
type SegmentRefresher interface {
	RefreshDynamicSegment(ctx context.Context, segmentID string) (int, error)
}

// SegmentHandler wires segment endpoints.
type SegmentHandler struct {
	reader    SegmentReader
	writer    SegmentWriter
	refresher SegmentRefresher
}

// NewSegmentHandler constructs the handler.
func NewSegmentHandler(r SegmentReader, w SegmentWriter, rf SegmentRefresher) *SegmentHandler {
	return &SegmentHandler{reader: r, writer: w, refresher: rf}
}

// RegisterRoutes mounts segment routes on the given chi router.
func (h *SegmentHandler) RegisterRoutes(r chi.Router) {
	r.Get("/api/segments", h.listSegments)
	r.Post("/api/segments", h.createSegment)
	r.Patch("/api/segments/{id}", h.updateSegment)
	r.Post("/api/segments/{id}/refresh", h.refreshSegment)
	r.Get("/api/segments/{id}/members", h.listMembers)
	r.Post("/api/segments/{id}/members", h.addMember)
	r.Delete("/api/segments/{id}/members/{partyId}", h.removeMember)
}

// GET /api/segments
func (h *SegmentHandler) listSegments(w http.ResponseWriter, r *http.Request) {
	segs, err := h.reader.ListSegments(r.Context())
	if err != nil {
		log.Printf("segment handler: list: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list segments")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"segments": segs})
}

// POST /api/segments
func (h *SegmentHandler) createSegment(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name        string  `json:"name"`
		Description string  `json:"description"`
		IsDynamic   bool    `json:"is_dynamic"`
		Definition  string  `json:"definition"`
		OwnerUserID *string `json:"owner_user_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	seg := &domain.Segment{
		Name:        body.Name,
		Description: body.Description,
		IsDynamic:   body.IsDynamic,
		Definition:  body.Definition,
		OwnerUserID: body.OwnerUserID,
	}
	if err := h.writer.CreateSegment(r.Context(), seg); err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("segment handler: create: %v", err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusCreated, seg)
}

// PATCH /api/segments/{id}
func (h *SegmentHandler) updateSegment(w http.ResponseWriter, r *http.Request) {
	segID := chi.URLParam(r, "id")
	seg, err := h.reader.GetSegment(r.Context(), segID)
	if err != nil {
		log.Printf("segment handler: update get: %v", err)
		writeError(w, http.StatusInternalServerError, "operation failed")
		return
	}
	if seg == nil {
		writeError(w, http.StatusNotFound, "segment not found")
		return
	}

	var body struct {
		Name        *string `json:"name"`
		Description *string `json:"description"`
		IsDynamic   *bool   `json:"is_dynamic"`
		Definition  *string `json:"definition"`
		OwnerUserID *string `json:"owner_user_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if body.Name != nil {
		seg.Name = *body.Name
	}
	if body.Description != nil {
		seg.Description = *body.Description
	}
	if body.IsDynamic != nil {
		seg.IsDynamic = *body.IsDynamic
	}
	if body.Definition != nil {
		seg.Definition = *body.Definition
	}
	if body.OwnerUserID != nil {
		seg.OwnerUserID = body.OwnerUserID
	}
	if err := h.writer.UpdateSegment(r.Context(), seg); err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("segment handler: update %s: %v", segID, err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusOK, seg)
}

// POST /api/segments/{id}/refresh
func (h *SegmentHandler) refreshSegment(w http.ResponseWriter, r *http.Request) {
	segID := chi.URLParam(r, "id")
	n, err := h.refresher.RefreshDynamicSegment(r.Context(), segID)
	if err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("segment handler: refresh %s: %v", segID, err)
			writeError(w, http.StatusInternalServerError, "refresh failed")
		}
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"segment_id": segID, "members_refreshed": n})
}

// GET /api/segments/{id}/members
func (h *SegmentHandler) listMembers(w http.ResponseWriter, r *http.Request) {
	segID := chi.URLParam(r, "id")
	members, err := h.reader.ListMembers(r.Context(), segID)
	if err != nil {
		log.Printf("segment handler: list members %s: %v", segID, err)
		writeError(w, http.StatusInternalServerError, "failed to list members")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"members": members})
}

// POST /api/segments/{id}/members   body: {"party_id":"..."}
func (h *SegmentHandler) addMember(w http.ResponseWriter, r *http.Request) {
	segID := chi.URLParam(r, "id")
	var body struct {
		PartyID string `json:"party_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.PartyID == "" {
		writeError(w, http.StatusBadRequest, "party_id is required")
		return
	}
	if err := h.writer.AddMember(r.Context(), segID, body.PartyID); err != nil {
		log.Printf("segment handler: add member %s→%s: %v", segID, body.PartyID, err)
		writeError(w, http.StatusInternalServerError, "operation failed")
		return
	}
	writeJSON(w, http.StatusCreated, map[string]string{"segment_id": segID, "party_id": body.PartyID})
}

// DELETE /api/segments/{id}/members/{partyId}
func (h *SegmentHandler) removeMember(w http.ResponseWriter, r *http.Request) {
	segID := chi.URLParam(r, "id")
	partyID := chi.URLParam(r, "partyId")
	if err := h.writer.RemoveMember(r.Context(), segID, partyID); err != nil {
		log.Printf("segment handler: remove member %s→%s: %v", segID, partyID, err)
		writeError(w, http.StatusInternalServerError, "operation failed")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "removed"})
}

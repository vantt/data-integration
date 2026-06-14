// Package http — Campaign HTTP handlers.
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

// CampaignReader covers read operations for campaigns.
type CampaignReader interface {
	GetCampaign(ctx context.Context, campaignID string) (*domain.Campaign, error)
	ListCampaigns(ctx context.Context) ([]domain.Campaign, error)
	ListTargets(ctx context.Context, campaignID, status string) ([]domain.CampaignTarget, error)
	GetROI(ctx context.Context, campaignID string) (*domain.CampaignROI, error)
}

// CampaignWriter covers campaign creation and mutation.
type CampaignWriter interface {
	CreateCampaign(ctx context.Context, c *domain.Campaign) error
	UpdateCampaign(ctx context.Context, campaignID string, patch *domain.Campaign) error
	GenerateTargets(ctx context.Context, campaignID string) (int, error)
	UpdateTargetStatus(ctx context.Context, campaignID, partyID, newStatus string) error
	AssignTarget(ctx context.Context, campaignID, partyID, userID string) error
	ScanConversions(ctx context.Context, campaignID string) (int, error)
}

// CampaignHandler wires campaign endpoints.
type CampaignHandler struct {
	reader CampaignReader
	writer CampaignWriter
}

// NewCampaignHandler constructs the handler.
func NewCampaignHandler(r CampaignReader, w CampaignWriter) *CampaignHandler {
	return &CampaignHandler{reader: r, writer: w}
}

// RegisterRoutes mounts campaign routes on the given chi router.
func (h *CampaignHandler) RegisterRoutes(r chi.Router) {
	r.Get("/api/campaigns", h.listCampaigns)
	r.Post("/api/campaigns", h.createCampaign)
	r.Patch("/api/campaigns/{id}", h.updateCampaign)
	r.Post("/api/campaigns/{id}/generate-targets", h.generateTargets)
	r.Get("/api/campaigns/{id}/targets", h.listTargets)
	r.Patch("/api/campaigns/{id}/targets/{partyId}", h.updateTarget)
	r.Post("/api/campaigns/{id}/scan-conversions", h.scanConversions)
	r.Get("/api/campaigns/{id}/roi", h.getROI)
}

// GET /api/campaigns
func (h *CampaignHandler) listCampaigns(w http.ResponseWriter, r *http.Request) {
	campaigns, err := h.reader.ListCampaigns(r.Context())
	if err != nil {
		log.Printf("campaign handler: list: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list campaigns")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"campaigns": campaigns})
}

// POST /api/campaigns
func (h *CampaignHandler) createCampaign(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name        string  `json:"name"`
		Objective   string  `json:"objective"`
		Channel     string  `json:"channel"`
		SegmentID   *string `json:"segment_id"`
		ScheduledAt *string `json:"scheduled_at"`
		CreatedBy   *string `json:"created_by"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	c := &domain.Campaign{
		Name:        body.Name,
		Objective:   body.Objective,
		Channel:     body.Channel,
		SegmentID:   body.SegmentID,
		ScheduledAt: body.ScheduledAt,
		CreatedBy:   body.CreatedBy,
	}
	if err := h.writer.CreateCampaign(r.Context(), c); err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("campaign handler: create: %v", err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusCreated, c)
}

// PATCH /api/campaigns/{id}
func (h *CampaignHandler) updateCampaign(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "id")
	var body struct {
		Name        string  `json:"name"`
		Objective   string  `json:"objective"`
		Channel     string  `json:"channel"`
		SegmentID   *string `json:"segment_id"`
		Status      string  `json:"status"`
		ScheduledAt *string `json:"scheduled_at"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	patch := &domain.Campaign{
		Name:        body.Name,
		Objective:   body.Objective,
		Channel:     body.Channel,
		SegmentID:   body.SegmentID,
		Status:      body.Status,
		ScheduledAt: body.ScheduledAt,
	}
	if err := h.writer.UpdateCampaign(r.Context(), campaignID, patch); err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("campaign handler: update %s: %v", campaignID, err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "campaign_id": campaignID})
}

// POST /api/campaigns/{id}/generate-targets
func (h *CampaignHandler) generateTargets(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "id")
	n, err := h.writer.GenerateTargets(r.Context(), campaignID)
	if err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("campaign handler: generate targets %s: %v", campaignID, err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"campaign_id": campaignID, "targets_created": n})
}

// GET /api/campaigns/{id}/targets?status=<status>
func (h *CampaignHandler) listTargets(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "id")
	status := r.URL.Query().Get("status")
	targets, err := h.reader.ListTargets(r.Context(), campaignID, status)
	if err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("campaign handler: list targets %s: %v", campaignID, err)
			writeError(w, http.StatusInternalServerError, "failed to list targets")
		}
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"targets": targets})
}

// PATCH /api/campaigns/{id}/targets/{partyId}
// body: {"status":"sent"} or {"assigned_user_id":"..."}
func (h *CampaignHandler) updateTarget(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "id")
	partyID := chi.URLParam(r, "partyId")

	var body struct {
		Status         *string `json:"status"`
		AssignedUserID *string `json:"assigned_user_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if body.Status != nil {
		if err := h.writer.UpdateTargetStatus(r.Context(), campaignID, partyID, *body.Status); err != nil {
			if domain.IsValidationError(err) {
				writeError(w, http.StatusBadRequest, err.Error())
			} else {
				log.Printf("campaign handler: update target status (%s,%s): %v", campaignID, partyID, err)
				writeError(w, http.StatusInternalServerError, "operation failed")
			}
			return
		}
	}
	if body.AssignedUserID != nil {
		if err := h.writer.AssignTarget(r.Context(), campaignID, partyID, *body.AssignedUserID); err != nil {
			if domain.IsValidationError(err) {
				writeError(w, http.StatusBadRequest, err.Error())
			} else {
				log.Printf("campaign handler: assign target (%s,%s): %v", campaignID, partyID, err)
				writeError(w, http.StatusInternalServerError, "operation failed")
			}
			return
		}
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// POST /api/campaigns/{id}/scan-conversions
func (h *CampaignHandler) scanConversions(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "id")
	n, err := h.writer.ScanConversions(r.Context(), campaignID)
	if err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("campaign handler: scan conversions %s: %v", campaignID, err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"campaign_id": campaignID, "newly_converted": n})
}

// GET /api/campaigns/{id}/roi
func (h *CampaignHandler) getROI(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "id")
	roi, err := h.reader.GetROI(r.Context(), campaignID)
	if err != nil {
		log.Printf("campaign handler: roi %s: %v", campaignID, err)
		writeError(w, http.StatusInternalServerError, "failed to compute ROI")
		return
	}
	writeJSON(w, http.StatusOK, roi)
}

// Package web — S10 Campaigns List + S11 Campaign Detail/Targets screen handlers.
// Inbound adapter: reads/writes via CampaignQuerier/CampaignWriter interfaces.
// No business logic here — delegates to application.CampaignService.
package web

import (
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

func init() {
	register(func(r chi.Router, d *Deps) {
		// S10 — Campaigns list.
		r.Get("/campaigns", d.handleCampaignsList)
		r.Get("/campaigns/modal/create", d.handleModalCreateCampaign)
		r.Post("/campaigns", d.handleCampaignCreate)

		// S11 — Campaign detail.
		r.Get("/campaigns/{campaignID}", d.handleCampaignDetail)
		r.Get("/campaigns/{campaignID}/modal/edit", d.handleModalEditCampaign)
		r.Patch("/campaigns/{campaignID}", d.handleCampaignUpdate)

		// Target actions (HTMX).
		r.Post("/campaigns/{campaignID}/generate-targets", d.handleGenerateTargets)
		r.Post("/campaigns/{campaignID}/scan-conversions", d.handleScanConversions)
		r.Get("/campaigns/{campaignID}/targets/{partyID}/modal/convert", d.handleModalConvert)
		r.Post("/campaigns/{campaignID}/targets/{partyID}/convert", d.handleRecordConversion)
		r.Patch("/campaigns/{campaignID}/targets/{partyID}/status", d.handleUpdateTargetStatus)
	})
}

// handleCampaignsList serves GET /campaigns — S10 full page.
func (d *Deps) handleCampaignsList(w http.ResponseWriter, r *http.Request) {
	campaigns, err := d.Campaigns.ListCampaigns(r.Context())
	if err != nil {
		log.Printf("campaigns list: %v", err)
		campaigns = []domain.Campaign{}
	}

	// Build segment name lookup.
	segmentNames := d.buildSegmentNameMap(r, campaigns)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.CampaignsPage(campaigns, segmentNames).Render(r.Context(), w); err != nil {
		log.Printf("campaigns list: render: %v", err)
	}
}

// handleModalCreateCampaign serves GET /campaigns/modal/create — M07 fragment.
func (d *Deps) handleModalCreateCampaign(w http.ResponseWriter, r *http.Request) {
	segments, err := d.Segments.ListSegments(r.Context())
	if err != nil {
		log.Printf("modal create campaign: list segments: %v", err)
		segments = []domain.Segment{}
	}
	users, err := d.AppUsers.ListActive(r.Context())
	if err != nil {
		log.Printf("modal create campaign: list users: %v", err)
		users = []domain.AppUser{}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalCreateCampaign(segments, users).Render(r.Context(), w); err != nil {
		log.Printf("modal create campaign: render: %v", err)
	}
}

// handleCampaignCreate serves POST /campaigns — create a new campaign.
func (d *Deps) handleCampaignCreate(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	c := &domain.Campaign{
		Name:      strings.TrimSpace(r.FormValue("name")),
		Objective: strings.TrimSpace(r.FormValue("objective")),
		Channel:   strings.TrimSpace(r.FormValue("channel")),
		Status:    "draft",
	}
	if sid := strings.TrimSpace(r.FormValue("segment_id")); sid != "" {
		c.SegmentID = &sid
	}
	if sa := strings.TrimSpace(r.FormValue("scheduled_at")); sa != "" {
		// Form gives YYYY-MM-DD; store as RFC3339 midnight ICT.
		ts := sa + "T00:00:00+07:00"
		c.ScheduledAt = &ts
	}

	if err := d.Campaigns.CreateCampaign(r.Context(), c); err != nil {
		log.Printf("campaign create: %v", err)
		http.Error(w, "Lỗi tạo chiến dịch: "+err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("HX-Redirect", "/campaigns/"+c.CampaignID)
	w.WriteHeader(http.StatusOK)
}

// handleCampaignDetail serves GET /campaigns/{campaignID} — S11 full page.
func (d *Deps) handleCampaignDetail(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")

	campaign, err := d.Campaigns.GetCampaign(r.Context(), campaignID)
	if err != nil || campaign == nil {
		http.Error(w, "Chiến dịch không tìm thấy", http.StatusNotFound)
		return
	}

	targets, err := d.Campaigns.ListTargets(r.Context(), campaignID, "")
	if err != nil {
		log.Printf("campaign detail: list targets %s: %v", campaignID, err)
		targets = []domain.CampaignTarget{}
	}

	roi, err := d.Campaigns.GetROI(r.Context(), campaignID)
	if err != nil {
		log.Printf("campaign detail: roi %s: %v", campaignID, err)
		roi = &domain.CampaignROI{CampaignID: campaignID, StatusCounts: map[string]int{}}
	}

	partyNames := d.buildPartyNameMap(r, targets)

	segmentName := ""
	if campaign.SegmentID != nil {
		if seg, err := d.Segments.GetSegment(r.Context(), *campaign.SegmentID); err == nil && seg != nil {
			segmentName = seg.Name
		}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.CampaignDetailPage(campaign, targets, roi, partyNames, segmentName).Render(r.Context(), w); err != nil {
		log.Printf("campaign detail: render: %v", err)
	}
}

// handleModalEditCampaign serves GET /campaigns/{campaignID}/modal/edit — M07 edit fragment.
func (d *Deps) handleModalEditCampaign(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")
	campaign, err := d.Campaigns.GetCampaign(r.Context(), campaignID)
	if err != nil || campaign == nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	segments, err := d.Segments.ListSegments(r.Context())
	if err != nil {
		segments = []domain.Segment{}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalEditCampaign(campaign, segments).Render(r.Context(), w); err != nil {
		log.Printf("modal edit campaign: render: %v", err)
	}
}

// handleCampaignUpdate serves PATCH /campaigns/{campaignID} — update campaign fields.
func (d *Deps) handleCampaignUpdate(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	patch := &domain.Campaign{
		Name:      strings.TrimSpace(r.FormValue("name")),
		Objective: strings.TrimSpace(r.FormValue("objective")),
		Channel:   strings.TrimSpace(r.FormValue("channel")),
	}
	if sid := strings.TrimSpace(r.FormValue("segment_id")); sid != "" {
		patch.SegmentID = &sid
	}

	if err := d.Campaigns.UpdateCampaign(r.Context(), campaignID, patch); err != nil {
		log.Printf("campaign update %s: %v", campaignID, err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("HX-Redirect", "/campaigns/"+campaignID)
	w.WriteHeader(http.StatusOK)
}

// handleGenerateTargets serves POST /campaigns/{campaignID}/generate-targets —
// populates crm_campaign_target from the segment; returns updated target list fragment.
func (d *Deps) handleGenerateTargets(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")

	created, err := d.Campaigns.GenerateTargets(r.Context(), campaignID)
	if err != nil {
		log.Printf("generate targets %s: %v", campaignID, err)
		// Still render what we have.
	}
	log.Printf("generate targets %s: created %d", campaignID, created)

	targets, err := d.Campaigns.ListTargets(r.Context(), campaignID, "")
	if err != nil {
		log.Printf("generate targets: list after generate %s: %v", campaignID, err)
		targets = []domain.CampaignTarget{}
	}

	partyNames := d.buildPartyNameMap(r, targets)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.CampaignTargetList(campaignID, targets, partyNames).Render(r.Context(), w); err != nil {
		log.Printf("generate targets: render: %v", err)
	}
}

// handleScanConversions serves POST /campaigns/{campaignID}/scan-conversions —
// auto-converts targets with matching orders; returns updated ROI fragment.
func (d *Deps) handleScanConversions(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")

	converted, err := d.Campaigns.ScanConversions(r.Context(), campaignID)
	if err != nil {
		log.Printf("scan conversions %s: %v", campaignID, err)
		// Graceful-empty: cache absent → return ROI with zeros.
	}
	log.Printf("scan conversions %s: converted %d", campaignID, converted)

	roi, err := d.Campaigns.GetROI(r.Context(), campaignID)
	if err != nil {
		log.Printf("scan conversions: roi %s: %v", campaignID, err)
		roi = &domain.CampaignROI{CampaignID: campaignID, StatusCounts: map[string]int{}}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.CampaignROIFragment(roi).Render(r.Context(), w); err != nil {
		log.Printf("scan conversions: render: %v", err)
	}
}

// handleModalConvert serves GET /campaigns/{campaignID}/targets/{partyID}/modal/convert — M12 fragment.
func (d *Deps) handleModalConvert(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")
	partyID := chi.URLParam(r, "partyID")

	partyName := partyID
	if party, err := d.Parties.GetByID(r.Context(), partyID); err == nil && party != nil {
		partyName = party.DisplayName
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalRecordConversion(campaignID, partyID, partyName).Render(r.Context(), w); err != nil {
		log.Printf("modal convert: render: %v", err)
	}
}

// handleRecordConversion serves POST /campaigns/{campaignID}/targets/{partyID}/convert —
// records a manual conversion (M12 submit).
func (d *Deps) handleRecordConversion(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")
	partyID := chi.URLParam(r, "partyID")

	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	orderCode := strings.TrimSpace(r.FormValue("order_code"))
	revenueStr := strings.TrimSpace(r.FormValue("revenue_vnd"))

	// Build a target patch: set status to converted + optional order/revenue fields.
	patch := &domain.CampaignTarget{
		CampaignID: campaignID,
		PartyID:    partyID,
	}
	if orderCode != "" {
		patch.ConvertedOrderCode = &orderCode
	}
	if revenueStr != "" {
		if rev, err := strconv.ParseInt(revenueStr, 10, 64); err == nil {
			patch.ConvertedRevenueVND = &rev
		}
	}

	if err := d.Campaigns.RecordConversion(r.Context(), patch); err != nil {
		log.Printf("record conversion %s/%s: %v", campaignID, partyID, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Close modal and trigger page reload.
	w.Header().Set("HX-Trigger", `{"closeModal":true}`)
	w.Header().Set("HX-Redirect", "/campaigns/"+campaignID)
	w.WriteHeader(http.StatusOK)
}

// handleUpdateTargetStatus serves PATCH /campaigns/{campaignID}/targets/{partyID}/status —
// updates a target status and returns an updated row fragment.
func (d *Deps) handleUpdateTargetStatus(w http.ResponseWriter, r *http.Request) {
	campaignID := chi.URLParam(r, "campaignID")
	partyID := chi.URLParam(r, "partyID")

	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	newStatus := strings.TrimSpace(r.FormValue("status"))

	if err := d.Campaigns.UpdateTargetStatus(r.Context(), campaignID, partyID, newStatus); err != nil {
		log.Printf("update target status %s/%s → %s: %v", campaignID, partyID, newStatus, err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	t, err := d.Campaigns.GetTarget(r.Context(), campaignID, partyID)
	if err != nil || t == nil {
		http.Error(w, "target not found", http.StatusNotFound)
		return
	}

	partyNames := map[string]string{}
	if party, err := d.Parties.GetByID(r.Context(), partyID); err == nil && party != nil {
		partyNames[partyID] = party.DisplayName
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.CampaignTargetRow(campaignID, *t, partyNames).Render(r.Context(), w); err != nil {
		log.Printf("update target status: render: %v", err)
	}
}

// ── helpers ───────────────────────────────────────────────────────────────────

// buildSegmentNameMap builds a segmentID → name lookup for the campaigns list.
func (d *Deps) buildSegmentNameMap(r *http.Request, campaigns []domain.Campaign) map[string]string {
	seen := map[string]bool{}
	out := map[string]string{}
	for _, c := range campaigns {
		if c.SegmentID == nil || seen[*c.SegmentID] {
			continue
		}
		seen[*c.SegmentID] = true
		if seg, err := d.Segments.GetSegment(r.Context(), *c.SegmentID); err == nil && seg != nil {
			out[*c.SegmentID] = seg.Name
		}
	}
	return out
}

// buildPartyNameMap builds a partyID → displayName lookup for a target list.
func (d *Deps) buildPartyNameMap(r *http.Request, targets []domain.CampaignTarget) map[string]string {
	out := map[string]string{}
	for _, t := range targets {
		if _, ok := out[t.PartyID]; ok {
			continue
		}
		if party, err := d.Parties.GetByID(r.Context(), t.PartyID); err == nil && party != nil {
			out[t.PartyID] = party.DisplayName
		}
	}
	return out
}

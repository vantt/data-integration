// Package web — S08 Segments List + S09 Segment Builder screen handlers.
// Inbound adapter: reads/writes via SegmentQuerier/SegmentWriter interfaces.
// No business logic here — all rule validation happens in application.SegmentService.
package web

import (
	"encoding/json"
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
		// S08 — Segments list.
		r.Get("/segments", d.handleSegmentsList)

		// S09 — Segment builder (new + edit).
		r.Get("/segments/new", d.handleSegmentNew)
		r.Post("/segments", d.handleSegmentCreate)
		r.Get("/segments/{segmentID}", d.handleSegmentEdit)
		r.Put("/segments/{segmentID}", d.handleSegmentUpdate)

		// Refresh dynamic members (HTMX — returns updated row fragment).
		r.Post("/segments/{segmentID}/refresh", d.handleSegmentRefresh)

		// Manual member management.
		r.Post("/segments/{segmentID}/members", d.handleSegmentAddMember)
		r.Delete("/segments/{segmentID}/members/{partyID}", d.handleSegmentRemoveMember)
	})
}

// handleSegmentsList serves GET /segments — S08 full page.
func (d *Deps) handleSegmentsList(w http.ResponseWriter, r *http.Request) {
	segments, err := d.Segments.ListSegments(r.Context())
	if err != nil {
		log.Printf("segments list: %v", err)
		segments = []domain.Segment{}
	}

	// Fetch member counts for all segments.
	counts := make(map[string]int, len(segments))
	for _, seg := range segments {
		members, err := d.Segments.ListMembers(r.Context(), seg.SegmentID)
		if err == nil {
			counts[seg.SegmentID] = len(members)
		}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.SegmentsPage(segments, counts).Render(r.Context(), w); err != nil {
		log.Printf("segments list: render: %v", err)
	}
}

// handleSegmentNew serves GET /segments/new — blank S09 builder form.
func (d *Deps) handleSegmentNew(w http.ResponseWriter, r *http.Request) {
	empty := &domain.Segment{}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.SegmentBuilderPage(empty, nil, true).Render(r.Context(), w); err != nil {
		log.Printf("segment new: render: %v", err)
	}
}

// handleSegmentCreate serves POST /segments — create a new segment.
func (d *Deps) handleSegmentCreate(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	seg := &domain.Segment{
		Name:        strings.TrimSpace(r.FormValue("name")),
		Description: strings.TrimSpace(r.FormValue("description")),
		IsDynamic:   r.FormValue("is_dynamic") == "true",
		Definition:  buildRuleDefinition(r),
	}

	if err := d.Segments.CreateSegment(r.Context(), seg); err != nil {
		log.Printf("segment create: %v", err)
		http.Error(w, "Lỗi tạo segment: "+err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("HX-Redirect", "/segments/"+seg.SegmentID)
	w.WriteHeader(http.StatusOK)
}

// handleSegmentEdit serves GET /segments/{segmentID} — S09 edit view.
func (d *Deps) handleSegmentEdit(w http.ResponseWriter, r *http.Request) {
	segmentID := chi.URLParam(r, "segmentID")
	seg, err := d.Segments.GetSegment(r.Context(), segmentID)
	if err != nil || seg == nil {
		http.Error(w, "Segment không tìm thấy", http.StatusNotFound)
		return
	}

	members, err := d.Segments.ListMembers(r.Context(), segmentID)
	if err != nil {
		log.Printf("segment edit: list members %s: %v", segmentID, err)
		members = []domain.SegmentMember{}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.SegmentBuilderPage(seg, members, false).Render(r.Context(), w); err != nil {
		log.Printf("segment edit: render: %v", err)
	}
}

// handleSegmentUpdate serves PUT /segments/{segmentID} — save segment changes.
func (d *Deps) handleSegmentUpdate(w http.ResponseWriter, r *http.Request) {
	segmentID := chi.URLParam(r, "segmentID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	seg := &domain.Segment{
		SegmentID:   segmentID,
		Name:        strings.TrimSpace(r.FormValue("name")),
		Description: strings.TrimSpace(r.FormValue("description")),
		IsDynamic:   r.FormValue("is_dynamic") == "true",
		Definition:  buildRuleDefinition(r),
	}

	if err := d.Segments.UpdateSegment(r.Context(), seg); err != nil {
		log.Printf("segment update %s: %v", segmentID, err)
		http.Error(w, "Lỗi cập nhật: "+err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("HX-Redirect", "/segments/"+segmentID)
	w.WriteHeader(http.StatusOK)
}

// handleSegmentRefresh serves POST /segments/{segmentID}/refresh —
// recompute dynamic members and return an updated row fragment.
func (d *Deps) handleSegmentRefresh(w http.ResponseWriter, r *http.Request) {
	segmentID := chi.URLParam(r, "segmentID")

	count, err := d.Segments.RefreshDynamicSegment(r.Context(), segmentID)
	if err != nil {
		log.Printf("segment refresh %s: %v", segmentID, err)
		// On error still return a row — show stale data.
		count = 0
	}

	seg, err := d.Segments.GetSegment(r.Context(), segmentID)
	if err != nil || seg == nil {
		http.Error(w, "segment not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.SegmentRowRefreshed(*seg, count).Render(r.Context(), w); err != nil {
		log.Printf("segment refresh: render: %v", err)
	}
}

// handleSegmentAddMember serves POST /segments/{segmentID}/members — add a party manually.
func (d *Deps) handleSegmentAddMember(w http.ResponseWriter, r *http.Request) {
	segmentID := chi.URLParam(r, "segmentID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	partyID := strings.TrimSpace(r.FormValue("party_id"))
	if partyID == "" {
		http.Error(w, "party_id required", http.StatusBadRequest)
		return
	}
	if err := d.Segments.AddMember(r.Context(), segmentID, partyID); err != nil {
		log.Printf("segment add member %s/%s: %v", segmentID, partyID, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("HX-Redirect", "/segments/"+segmentID)
	w.WriteHeader(http.StatusOK)
}

// handleSegmentRemoveMember serves DELETE /segments/{segmentID}/members/{partyID}.
func (d *Deps) handleSegmentRemoveMember(w http.ResponseWriter, r *http.Request) {
	segmentID := chi.URLParam(r, "segmentID")
	partyID := chi.URLParam(r, "partyID")
	if err := d.Segments.RemoveMember(r.Context(), segmentID, partyID); err != nil {
		log.Printf("segment remove member %s/%s: %v", segmentID, partyID, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("HX-Redirect", "/segments/"+segmentID)
	w.WriteHeader(http.StatusOK)
}

// ── helpers ───────────────────────────────────────────────────────────────────

// buildRuleDefinition constructs the segment rule JSON from whitelisted form fields.
// Only emits keys that have non-zero values — empty keys are omitted.
// Values are taken from form fields, never interpolated into SQL.
func buildRuleDefinition(r *http.Request) string {
	rule := map[string]any{}

	// value_group — multi-checkbox.
	if vgs := r.Form["rule_value_group"]; len(vgs) > 0 {
		rule["value_group"] = vgs
	}

	// customer_status — single select.
	if cs := strings.TrimSpace(r.FormValue("rule_customer_status")); cs != "" {
		rule["customer_status"] = cs
	}

	// days_since_last_order_gte — numeric.
	if ds := strings.TrimSpace(r.FormValue("rule_days_since")); ds != "" {
		if n, err := strconv.Atoi(ds); err == nil && n > 0 {
			rule["days_since_last_order_gte"] = n
		}
	}

	// channel_preference — free text.
	if ch := strings.TrimSpace(r.FormValue("rule_channel")); ch != "" {
		rule["channel_preference"] = ch
	}

	if len(rule) == 0 {
		return ""
	}
	b, err := json.Marshal(rule)
	if err != nil {
		return ""
	}
	return string(b)
}

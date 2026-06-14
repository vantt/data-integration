// Package web — S13 Settings screen handler.
// Inbound adapter: reads/writes via SettingsReader/SettingsWriter interfaces.
// No business logic here — delegates to application.ProfileService.
package web

import (
	"log"
	"net/http"
	"regexp"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// hexColorRe validates a CSS hex color in the form #RRGGBB.
var hexColorRe = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)

// isValidHexColor returns true when color is empty (optional) or a valid #RRGGBB string.
func isValidHexColor(color string) bool {
	if color == "" {
		return true
	}
	return hexColorRe.MatchString(color)
}

func init() {
	register(func(r chi.Router, d *Deps) {
		// S13 — Settings page.
		r.Get("/settings", d.handleSettings)

		// Custom field def CRUD.
		r.Get("/settings/custom-fields/modal/create", d.handleModalCustomFieldCreate)
		r.Post("/settings/custom-fields", d.handleCustomFieldCreate)
		r.Get("/settings/custom-fields/{fieldID}/modal/edit", d.handleModalCustomFieldEdit)
		r.Patch("/settings/custom-fields/{fieldID}", d.handleCustomFieldUpdate)

		// Tag CRUD.
		r.Get("/settings/tags/modal/create", d.handleModalTagCreate)
		r.Post("/settings/tags", d.handleTagCreate)
	})
}

// handleSettings serves GET /settings — S13 full page.
func (d *Deps) handleSettings(w http.ResponseWriter, r *http.Request) {
	activeTab := r.URL.Query().Get("tab")
	if activeTab == "" {
		activeTab = "custom_fields"
	}

	fields, err := d.SettingsMgr.ListCustomFieldDefs(r.Context(), "party")
	if err != nil {
		log.Printf("settings: list custom field defs: %v", err)
		fields = []domain.CustomFieldDef{}
	}

	tags, err := d.SettingsMgr.ListTags(r.Context(), "")
	if err != nil {
		log.Printf("settings: list tags: %v", err)
		tags = []domain.Tag{}
	}

	users, err := d.AppUsers.ListActive(r.Context())
	if err != nil {
		log.Printf("settings: list users: %v", err)
		users = []domain.AppUser{}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.SettingsPage(activeTab, fields, tags, users).Render(r.Context(), w); err != nil {
		log.Printf("settings: render: %v", err)
	}
}

// handleModalCustomFieldCreate serves GET /settings/custom-fields/modal/create — M13 (new).
func (d *Deps) handleModalCustomFieldCreate(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalCustomFieldDef(nil, true).Render(r.Context(), w); err != nil {
		log.Printf("modal custom field create: render: %v", err)
	}
}

// handleCustomFieldCreate serves POST /settings/custom-fields — create a new custom field def.
func (d *Deps) handleCustomFieldCreate(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	dataType := strings.TrimSpace(r.FormValue("data_type"))
	if !domain.IsValidDataType(dataType) {
		http.Error(w, "invalid data_type: "+dataType, http.StatusBadRequest)
		return
	}

	def := &domain.CustomFieldDef{
		FieldID:    uuid.New().String(),
		EntityType: "party",
		FieldKey:   strings.TrimSpace(r.FormValue("field_key")),
		Label:      strings.TrimSpace(r.FormValue("label")),
		DataType:   dataType,
		IsRequired: r.FormValue("is_required") == "true",
		IsActive:   true,
		Options:    parseOptions(r.FormValue("options")),
	}

	if def.FieldKey == "" || def.Label == "" {
		http.Error(w, "field_key and label required", http.StatusBadRequest)
		return
	}

	if err := d.SettingsMgr.CreateCustomFieldDef(r.Context(), def); err != nil {
		log.Printf("custom field create: %v", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("HX-Redirect", "/settings?tab=custom_fields")
	w.WriteHeader(http.StatusOK)
}

// handleModalCustomFieldEdit serves GET /settings/custom-fields/{fieldID}/modal/edit — M13 (edit).
func (d *Deps) handleModalCustomFieldEdit(w http.ResponseWriter, r *http.Request) {
	fieldID := chi.URLParam(r, "fieldID")
	def, err := d.SettingsMgr.GetCustomFieldDef(r.Context(), fieldID)
	if err != nil || def == nil {
		http.Error(w, "field not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalCustomFieldDef(def, false).Render(r.Context(), w); err != nil {
		log.Printf("modal custom field edit: render: %v", err)
	}
}

// handleCustomFieldUpdate serves PATCH /settings/custom-fields/{fieldID} — update field def.
// field_key is intentionally NOT updated here: the underlying SQL (UpdateCustomFieldDef) only
// touches label, options, is_required, is_active, sort_order — field_key is immutable after
// creation to preserve JSON blob keys in existing CustomerProfile.Custom records.
func (d *Deps) handleCustomFieldUpdate(w http.ResponseWriter, r *http.Request) {
	fieldID := chi.URLParam(r, "fieldID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	dataType := strings.TrimSpace(r.FormValue("data_type"))
	if !domain.IsValidDataType(dataType) {
		http.Error(w, "invalid data_type: "+dataType, http.StatusBadRequest)
		return
	}

	def := &domain.CustomFieldDef{
		FieldID:    fieldID,
		Label:      strings.TrimSpace(r.FormValue("label")),
		DataType:   dataType,
		IsRequired: r.FormValue("is_required") == "true",
		IsActive:   true,
		Options:    parseOptions(r.FormValue("options")),
		// FieldKey is NOT set here — the update SQL does not touch it (immutable after creation).
	}

	if err := d.SettingsMgr.UpdateCustomFieldDef(r.Context(), def); err != nil {
		log.Printf("custom field update %s: %v", fieldID, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("HX-Redirect", "/settings?tab=custom_fields")
	w.WriteHeader(http.StatusOK)
}

// handleModalTagCreate serves GET /settings/tags/modal/create — M14.
func (d *Deps) handleModalTagCreate(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalCreateTag().Render(r.Context(), w); err != nil {
		log.Printf("modal tag create: render: %v", err)
	}
}

// handleTagCreate serves POST /settings/tags — create a new tag.
// Note: domain.Tag has no Label field; the form label field is not persisted.
func (d *Deps) handleTagCreate(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	name := strings.TrimSpace(r.FormValue("name"))
	if name == "" {
		http.Error(w, "name required", http.StatusBadRequest)
		return
	}

	color := strings.TrimSpace(r.FormValue("color"))
	if !isValidHexColor(color) {
		http.Error(w, "invalid color: must be #RRGGBB or empty", http.StatusBadRequest)
		return
	}

	tag := &domain.Tag{
		TagID:    uuid.New().String(),
		Name:     name,
		Category: strings.TrimSpace(r.FormValue("category")),
		Color:    color,
	}

	if err := d.SettingsMgr.CreateTag(r.Context(), tag); err != nil {
		log.Printf("tag create: %v", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("HX-Redirect", "/settings?tab=tags")
	w.WriteHeader(http.StatusOK)
}

// ── helper ────────────────────────────────────────────────────────────────────

// parseOptions splits newline-separated option values for select/multiselect fields.
func parseOptions(raw string) []string {
	if strings.TrimSpace(raw) == "" {
		return nil
	}
	lines := strings.Split(raw, "\n")
	out := make([]string, 0, len(lines))
	for _, l := range lines {
		if v := strings.TrimSpace(l); v != "" {
			out = append(out, v)
		}
	}
	return out
}

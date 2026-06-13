// Package http — Customer 360 HTTP handlers.
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

// ─── service interfaces (dependency-inversion; handler owns no concrete types) ─

// ProfileQuerier is the read interface for the profile handler.
type ProfileQuerier interface {
	GetProfile(ctx context.Context, partyID string) (*domain.CustomerProfile, error)
	GetParty360(ctx context.Context, partyID string) (*domain.Party360, error)
}

// PartyLookup is the minimal party read interface the 360 handler needs
// to distinguish "not found" from "merged" on GetParty360 misses.
// Satisfied by ports.PartyRepository (GetByID).
type PartyLookup interface {
	GetByID(ctx context.Context, partyID string) (*domain.Party, error)
}

// ProfileWriter is the write interface for profile upsert + custom updates.
type ProfileWriter interface {
	UpsertProfile(ctx context.Context, p *domain.CustomerProfile) error
	UpdateCustom(ctx context.Context, partyID string, newValues map[string]string) error
}

// TagManager covers tag attach/detach and listing.
type TagManager interface {
	AttachTag(ctx context.Context, partyID, tagID string, taggedBy *string) error
	DetachTag(ctx context.Context, partyID, tagID string) error
	ListPartyTags(ctx context.Context, partyID string) ([]domain.Tag, error)
}

// NoteManager covers note creation and listing.
type NoteManager interface {
	AddNote(ctx context.Context, partyID, body string, authorUserID *string) (*domain.Note, error)
	ListNotes(ctx context.Context, partyID string) ([]domain.Note, error)
}

// CustomFieldAdmin covers custom-field def CRUD.
type CustomFieldAdmin interface {
	ListCustomFieldDefs(ctx context.Context, entityType string) ([]domain.CustomFieldDef, error)
	CreateCustomFieldDef(ctx context.Context, d *domain.CustomFieldDef) error
}

// ─── handler ──────────────────────────────────────────────────────────────────

// Customer360Handler wires all Customer 360 endpoints.
type Customer360Handler struct {
	profileQ    ProfileQuerier
	profileW    ProfileWriter
	tags        TagManager
	notes       NoteManager
	cfAdmin     CustomFieldAdmin
	partyLookup PartyLookup
}

// NewCustomer360Handler constructs the handler.
func NewCustomer360Handler(
	pq ProfileQuerier,
	pw ProfileWriter,
	tm TagManager,
	nm NoteManager,
	cfa CustomFieldAdmin,
	pl PartyLookup,
) *Customer360Handler {
	return &Customer360Handler{
		profileQ:    pq,
		profileW:    pw,
		tags:        tm,
		notes:       nm,
		cfAdmin:     cfa,
		partyLookup: pl,
	}
}

// RegisterRoutes mounts all Customer 360 routes on the given chi router.
func (h *Customer360Handler) RegisterRoutes(r chi.Router) {
	r.Get("/api/parties/{id}/profile", h.getProfile)
	r.Put("/api/parties/{id}/profile", h.putProfile)
	r.Post("/api/parties/{id}/tags", h.attachTag)
	r.Delete("/api/parties/{id}/tags/{tagId}", h.detachTag)
	r.Post("/api/parties/{id}/notes", h.addNote)
	r.Get("/api/parties/{id}/notes", h.listNotes)
	r.Get("/api/parties/{id}/360", h.getParty360)
	r.Get("/api/custom-fields", h.listCustomFields)
	r.Post("/api/custom-fields", h.createCustomField)
}

// GET /api/parties/{id}/profile
func (h *Customer360Handler) getProfile(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")
	p, err := h.profileQ.GetProfile(r.Context(), partyID)
	if err != nil {
		log.Printf("customer360: get profile %s: %v", partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to get profile")
		return
	}
	if p == nil {
		writeError(w, http.StatusNotFound, "profile not found")
		return
	}
	writeJSON(w, http.StatusOK, p)
}

// PUT /api/parties/{id}/profile
// Accepts a partial profile body. custom_fields map is processed via UpdateCustom.
func (h *Customer360Handler) putProfile(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")

	var body struct {
		OwnerUserID       *string           `json:"owner_user_id"`
		LifecycleStage    string            `json:"lifecycle_stage"`
		AcquisitionSource string            `json:"acquisition_source"`
		Birthday          string            `json:"birthday"`
		Address           string            `json:"address"`
		Preferences       string            `json:"preferences"`
		ConsentContact    bool              `json:"consent_contact"`
		CustomFields      map[string]string `json:"custom_fields"` // validated before merge
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	// Preserve existing custom JSON when custom_fields are not supplied in this request.
	// Load once; reuse the existing value so UpsertProfile never silently wipes custom data.
	existingCustom := "{}"
	if len(body.CustomFields) == 0 {
		existing, err := h.profileQ.GetProfile(r.Context(), partyID)
		if err != nil {
			log.Printf("customer360: get existing profile %s: %v", partyID, err)
			writeError(w, http.StatusInternalServerError, "failed to read existing profile")
			return
		}
		if existing != nil && existing.Custom != "" {
			existingCustom = existing.Custom
		}
	}

	p := &domain.CustomerProfile{
		PartyID:           partyID,
		OwnerUserID:       body.OwnerUserID,
		LifecycleStage:    body.LifecycleStage,
		AcquisitionSource: body.AcquisitionSource,
		Birthday:          body.Birthday,
		Address:           body.Address,
		Preferences:       body.Preferences,
		ConsentContact:    body.ConsentContact,
		Custom:            existingCustom,
	}
	if err := h.profileW.UpsertProfile(r.Context(), p); err != nil {
		log.Printf("customer360: upsert profile %s: %v", partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to update profile")
		return
	}

	// If custom_fields were supplied, run validated merge separately.
	if len(body.CustomFields) > 0 {
		if err := h.profileW.UpdateCustom(r.Context(), partyID, body.CustomFields); err != nil {
			log.Printf("customer360: update custom %s: %v", partyID, err)
			writeError(w, http.StatusBadRequest, err.Error())
			return
		}
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "party_id": partyID})
}

// POST /api/parties/{id}/tags   body: {"tag_id":"...", "tagged_by":"..."}
func (h *Customer360Handler) attachTag(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")
	var body struct {
		TagID    string  `json:"tag_id"`
		TaggedBy *string `json:"tagged_by,omitempty"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.TagID == "" {
		writeError(w, http.StatusBadRequest, "tag_id required")
		return
	}
	if err := h.tags.AttachTag(r.Context(), partyID, body.TagID, body.TaggedBy); err != nil {
		log.Printf("customer360: attach tag %s→%s: %v", body.TagID, partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to attach tag")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// DELETE /api/parties/{id}/tags/{tagId}
func (h *Customer360Handler) detachTag(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")
	tagID := chi.URLParam(r, "tagId")
	if err := h.tags.DetachTag(r.Context(), partyID, tagID); err != nil {
		log.Printf("customer360: detach tag %s→%s: %v", tagID, partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to detach tag")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// POST /api/parties/{id}/notes   body: {"body":"...", "author_user_id":"..."}
func (h *Customer360Handler) addNote(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")
	var body struct {
		Body         string  `json:"body"`
		AuthorUserID *string `json:"author_user_id,omitempty"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Body == "" {
		writeError(w, http.StatusBadRequest, "body required")
		return
	}
	note, err := h.notes.AddNote(r.Context(), partyID, body.Body, body.AuthorUserID)
	if err != nil {
		log.Printf("customer360: add note %s: %v", partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to add note")
		return
	}
	writeJSON(w, http.StatusCreated, note)
}

// GET /api/parties/{id}/notes
func (h *Customer360Handler) listNotes(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")
	notes, err := h.notes.ListNotes(r.Context(), partyID)
	if err != nil {
		log.Printf("customer360: list notes %s: %v", partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to list notes")
		return
	}
	if notes == nil {
		notes = []domain.Note{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"party_id": partyID, "notes": notes})
}

// GET /api/parties/{id}/360
// Returns 404 when the party does not exist, or 409 with body
// {"error":"party_merged","merged_into":"<id>"} when the party was merged.
func (h *Customer360Handler) getParty360(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "id")
	v, err := h.profileQ.GetParty360(r.Context(), partyID)
	if err != nil {
		log.Printf("customer360: get party360 %s: %v", partyID, err)
		writeError(w, http.StatusInternalServerError, "failed to get party 360")
		return
	}
	if v == nil {
		// Distinguish merged-party from genuinely absent party.
		party, lookupErr := h.partyLookup.GetByID(r.Context(), partyID)
		if lookupErr != nil {
			log.Printf("customer360: party lookup for 360 %s: %v", partyID, lookupErr)
			writeError(w, http.StatusNotFound, "party not found")
			return
		}
		if party != nil && party.IsMerged {
			mergedInto := ""
			if party.MergedInto != nil {
				mergedInto = *party.MergedInto
			}
			writeJSON(w, http.StatusConflict, map[string]string{
				"error":      "party_merged",
				"merged_into": mergedInto,
			})
			return
		}
		writeError(w, http.StatusNotFound, "party not found")
		return
	}
	writeJSON(w, http.StatusOK, v)
}

// GET /api/custom-fields?entity_type=party
func (h *Customer360Handler) listCustomFields(w http.ResponseWriter, r *http.Request) {
	entityType := r.URL.Query().Get("entity_type")
	if entityType == "" {
		entityType = "party"
	}
	defs, err := h.cfAdmin.ListCustomFieldDefs(r.Context(), entityType)
	if err != nil {
		log.Printf("customer360: list custom fields: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list custom fields")
		return
	}
	if defs == nil {
		defs = []domain.CustomFieldDef{}
	}
	writeJSON(w, http.StatusOK, map[string]any{"entity_type": entityType, "fields": defs})
}

// POST /api/custom-fields
func (h *Customer360Handler) createCustomField(w http.ResponseWriter, r *http.Request) {
	var body domain.CustomFieldDef
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if body.FieldKey == "" || body.Label == "" || body.DataType == "" {
		writeError(w, http.StatusBadRequest, "field_key, label, and data_type are required")
		return
	}
	if !domain.IsValidDataType(body.DataType) {
		writeError(w, http.StatusBadRequest, "data_type must be one of: text, number, date, bool, select, multiselect")
		return
	}
	if err := h.cfAdmin.CreateCustomFieldDef(r.Context(), &body); err != nil {
		log.Printf("customer360: create custom field: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to create custom field")
		return
	}
	writeJSON(w, http.StatusCreated, body)
}

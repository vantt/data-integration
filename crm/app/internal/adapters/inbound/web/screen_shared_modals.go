// Package web — shared modal endpoints used across multiple screens.
// M02 Create Party, M04 Assign Owner — registered via init().
// No business logic here; delegates to existing application services.
package web

import (
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

func init() {
	register(func(r chi.Router, d *Deps) {
		// M02 — Create party modal + submit.
		r.Get("/parties/modal/create", d.handleSharedModalCreateParty)
		r.Post("/parties", d.handleSharedCreateParty)

		// M04 — Assign owner modal + submit (used from Customer 360).
		r.Get("/customers/{partyID}/modal/assign-owner", d.handleModalAssignOwner)
		r.Post("/customers/{partyID}/assign-owner", d.handleAssignOwner)
	})
}

// handleSharedModalCreateParty serves GET /parties/modal/create — M02 fragment.
func (d *Deps) handleSharedModalCreateParty(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalCreateParty().Render(r.Context(), w); err != nil {
		log.Printf("modal create party: render: %v", err)
	}
}

// handleSharedCreateParty serves POST /parties — M02 submit: create party + phone identity.
func (d *Deps) handleSharedCreateParty(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	displayName := strings.TrimSpace(r.FormValue("display_name"))
	phone := strings.TrimSpace(r.FormValue("phone"))
	email := strings.TrimSpace(r.FormValue("email"))

	if displayName == "" || phone == "" {
		http.Error(w, "display_name and phone required", http.StatusBadRequest)
		return
	}

	now := time.Now().UTC().Format("2006-01-02T15:04:05.000Z")
	partyID := uuid.New().String()

	party := &domain.Party{
		PartyID:      partyID,
		PartyType:    "person",
		DisplayName:  displayName,
		PrimaryPhone: phone,
		PrimaryEmail: email,
		Status:       "active",
		CreatedAt:    now,
		UpdatedAt:    now,
	}

	phoneIdentity := &domain.PartyIdentity{
		IdentityID:    uuid.New().String(),
		PartyID:       partyID,
		SourceSystem:  "manual",
		IdentityType:  "phone",
		IdentityValue: phone,
		Confidence:    1.0,
		IsPrimary:     true,
		CreatedAt:     now,
	}

	if err := d.PartyCreator.CreateWithIdentities(r.Context(), party, []*domain.PartyIdentity{phoneIdentity}); err != nil {
		log.Printf("create party: %v", err)
		http.Error(w, "Lỗi tạo khách hàng: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// Navigate to the new party's Customer 360.
	w.Header().Set("HX-Redirect", "/customers/"+partyID)
	w.WriteHeader(http.StatusOK)
}

// handleModalAssignOwner serves GET /customers/{partyID}/modal/assign-owner — M04 fragment.
func (d *Deps) handleModalAssignOwner(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "partyID")

	// Load current owner from profile.
	var currentOwnerID *string
	if p360, err := d.Profile.GetParty360(r.Context(), partyID); err == nil && p360 != nil {
		currentOwnerID = p360.OwnerUserID
	}

	users, err := d.AppUsers.ListActive(r.Context())
	if err != nil {
		log.Printf("modal assign owner: list users: %v", err)
		users = []domain.AppUser{}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalAssignOwner(partyID, currentOwnerID, users).Render(r.Context(), w); err != nil {
		log.Printf("modal assign owner: render: %v", err)
	}
}

// handleAssignOwner serves POST /customers/{partyID}/assign-owner — M04 submit.
func (d *Deps) handleAssignOwner(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "partyID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	ownerUserID := strings.TrimSpace(r.FormValue("owner_user_id"))
	if ownerUserID == "" {
		http.Error(w, "owner_user_id required", http.StatusBadRequest)
		return
	}

	// Upsert profile with updated owner_user_id.
	now := time.Now().UTC().Format("2006-01-02T15:04:05.000Z")
	profile := &domain.CustomerProfile{
		PartyID:     partyID,
		OwnerUserID: &ownerUserID,
		Custom:      "{}",
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if err := d.OwnerAssigner.UpsertProfile(r.Context(), profile); err != nil {
		log.Printf("assign owner %s: %v", partyID, err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Close modal and reload the customer 360 page.
	w.Header().Set("HX-Trigger", `{"closeModal":true}`)
	w.Header().Set("HX-Redirect", "/customers/"+partyID)
	w.WriteHeader(http.StatusOK)
}

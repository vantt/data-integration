// Package web — S03 Customer 360 Detail screen handler.
// Inbound adapter: reads from ProfileReader, InsightReader, IdentityReader,
// ActivityReader, NoteReader, TaskPartyQuerier. No business logic.
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
		r.Get("/customers/{partyID}", d.handleCustomer360)
		r.Get("/customers/{partyID}/panels/{panel}", d.handleCustomer360Panel)
		r.Post("/customers/{partyID}/notes", d.handleAddNote)
	})
}

// handleCustomer360 serves GET /customers/{partyID} — full 360 detail page.
func (d *Deps) handleCustomer360(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "partyID")
	activeTab := r.URL.Query().Get("tab")
	if activeTab == "" {
		activeTab = "insight"
	}

	party360, identities, err := d.load360Base(r, partyID)
	if err != nil {
		log.Printf("c360: load base %s: %v", partyID, err)
		http.Error(w, "Không tìm thấy khách hàng", http.StatusNotFound)
		return
	}
	if party360 == nil {
		http.Error(w, "Không tìm thấy khách hàng", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.Customer360Page(party360, identities, activeTab).Render(r.Context(), w); err != nil {
		log.Printf("c360: render page %s: %v", partyID, err)
	}
}

// handleCustomer360Panel serves GET /customers/{partyID}/panels/{panel} — HTMX panel fragments.
func (d *Deps) handleCustomer360Panel(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "partyID")
	panel := chi.URLParam(r, "panel")

	w.Header().Set("Content-Type", "text/html; charset=utf-8")

	switch panel {
	case "insight":
		d.renderInsightPanel(w, r, partyID)
	case "orders":
		d.renderOrdersPanel(w, r, partyID)
	case "timeline":
		d.renderTimelinePanel(w, r, partyID)
	case "tasks":
		d.renderTasksPanel(w, r, partyID)
	case "notes":
		d.renderNotesPanel(w, r, partyID)
	default:
		http.Error(w, "panel not found", http.StatusNotFound)
	}
}

// handleAddNote serves POST /customers/{partyID}/notes — adds a note; returns NoteCard fragment.
func (d *Deps) handleAddNote(w http.ResponseWriter, r *http.Request) {
	partyID := chi.URLParam(r, "partyID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	body := strings.TrimSpace(r.FormValue("body"))
	if body == "" {
		http.Error(w, "body required", http.StatusBadRequest)
		return
	}

	note, err := d.Notes.AddNote(r.Context(), partyID, body, nil)
	if err != nil {
		log.Printf("c360: add note %s: %v", partyID, err)
		http.Error(w, "failed to add note", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.NoteCard(*note).Render(r.Context(), w); err != nil {
		log.Printf("c360: render note card: %v", err)
	}
}

// ── panel renderers ────────────────────────────────────────────────────────────

func (d *Deps) renderInsightPanel(w http.ResponseWriter, r *http.Request, partyID string) {
	// Resolve sapo_customer identity to get customerID for cache lookup.
	customerID := d.resolveSapoCustomerID(r, partyID)
	var insight *domain.CacheInsight
	if customerID > 0 {
		var err error
		insight, err = d.Insight.GetCustomerInsight(r.Context(), customerID)
		if err != nil {
			log.Printf("c360 insight: get insight %s: %v", partyID, err)
		}
	}
	if err := templates.P01InsightPanel(insight).Render(r.Context(), w); err != nil {
		log.Printf("c360 insight: render panel: %v", err)
	}
}

func (d *Deps) renderOrdersPanel(w http.ResponseWriter, r *http.Request, partyID string) {
	customerID := d.resolveSapoCustomerID(r, partyID)
	var orders []domain.RecentOrder
	if customerID > 0 {
		insight, err := d.Insight.GetCustomerInsight(r.Context(), customerID)
		if err != nil {
			log.Printf("c360 orders: get insight %s: %v", partyID, err)
		} else if insight != nil {
			orders = insight.RecentOrders
		}
	}
	if err := templates.P02OrderHistoryPanel(orders).Render(r.Context(), w); err != nil {
		log.Printf("c360 orders: render panel: %v", err)
	}
}

func (d *Deps) renderTimelinePanel(w http.ResponseWriter, r *http.Request, partyID string) {
	activities, err := d.Activities.ListTimeline(r.Context(), partyID)
	if err != nil {
		log.Printf("c360 timeline: list %s: %v", partyID, err)
		activities = []domain.Activity{}
	}
	if err := templates.P03ActivityTimelinePanel(activities).Render(r.Context(), w); err != nil {
		log.Printf("c360 timeline: render panel: %v", err)
	}
}

func (d *Deps) renderTasksPanel(w http.ResponseWriter, r *http.Request, partyID string) {
	tasks, err := d.PartyTasks.ListByParty(r.Context(), partyID)
	if err != nil {
		log.Printf("c360 tasks: list %s: %v", partyID, err)
		tasks = []domain.Task{}
	}
	if err := templates.P04TasksPanel(tasks, partyID).Render(r.Context(), w); err != nil {
		log.Printf("c360 tasks: render panel: %v", err)
	}
}

func (d *Deps) renderNotesPanel(w http.ResponseWriter, r *http.Request, partyID string) {
	notes, err := d.Notes.ListNotes(r.Context(), partyID)
	if err != nil {
		log.Printf("c360 notes: list %s: %v", partyID, err)
		notes = []domain.Note{}
	}
	if err := templates.P05NotesPanel(notes, partyID).Render(r.Context(), w); err != nil {
		log.Printf("c360 notes: render panel: %v", err)
	}
}

// ── shared helpers ─────────────────────────────────────────────────────────────

// load360Base fetches the Party360 view + identities.
// Returns (nil, nil, nil) when the party is not found.
func (d *Deps) load360Base(r *http.Request, partyID string) (
	*domain.Party360,
	[]domain.PartyIdentity,
	error,
) {
	party360, err := d.Profile.GetParty360(r.Context(), partyID)
	if err != nil {
		return nil, nil, err
	}
	if party360 == nil {
		return nil, nil, nil
	}

	identities, err := d.Identities.ListIdentities(r.Context(), partyID)
	if err != nil {
		log.Printf("c360: list identities %s: %v", partyID, err)
		identities = []domain.PartyIdentity{}
	}

	return party360, identities, nil
}

// resolveSapoCustomerID finds the Sapo customer_id from a party's identities.
// Returns 0 if not found or on error.
func (d *Deps) resolveSapoCustomerID(r *http.Request, partyID string) int64 {
	identities, err := d.Identities.ListIdentities(r.Context(), partyID)
	if err != nil {
		return 0
	}
	for _, id := range identities {
		if id.IdentityType == "sapo_customer" {
			n, err := strconv.ParseInt(id.IdentityValue, 10, 64)
			if err == nil {
				return n
			}
		}
	}
	return 0
}

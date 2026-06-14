// Package web — S05 Inbox + S06 Conversation Detail screen handlers.
// Inbound adapter: reads/writes via ConversationLister, ConvWriter, ConvLinker,
// AppUserLister, PartyLister, ActivityLogger. No business logic here.
package web

import (
	"log"
	"net/http"
	"strings"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

func init() {
	register(func(r chi.Router, d *Deps) {
		// S05 — Inbox list.
		r.Get("/inbox", d.handleInbox)

		// S06 — Conversation detail.
		r.Get("/inbox/{conversationID}", d.handleConversationDetail)

		// M09 — Assign conversation modal + submit.
		r.Get("/inbox/{conversationID}/modal/assign", d.handleModalAssignConversation)
		r.Post("/inbox/{conversationID}/assign", d.handleAssignConversation)

		// M10 — Close conversation modal + submit.
		r.Get("/inbox/{conversationID}/modal/close", d.handleModalCloseConversation)
		r.Post("/inbox/{conversationID}/close", d.handleCloseConversation)

		// M11 — Link party modal + party search fragment + submit.
		r.Get("/inbox/{conversationID}/modal/link-party", d.handleModalLinkParty)
		r.Get("/inbox/{conversationID}/parties/search", d.handleInboxPartySearch)
		r.Post("/inbox/{conversationID}/link-party", d.handleLinkParty)

		// M08 — Log activity from S06.
		r.Get("/inbox/{conversationID}/modal/log-activity", d.handleModalLogActivityConv)
		r.Post("/inbox/{conversationID}/log-activity", d.handleLogActivityOnConv)
	})
}

// ── S05 Inbox ─────────────────────────────────────────────────────────────────

func (d *Deps) handleInbox(w http.ResponseWriter, r *http.Request) {
	status := r.URL.Query().Get("status")
	assignee := r.URL.Query().Get("assignee")

	convs, err := d.Conversations.ListInbox(r.Context(), assignee, status)
	if err != nil {
		log.Printf("inbox: list: %v", err)
		convs = []domain.Conversation{}
	}

	// Build partyID → displayName for rows that have a linked party.
	partyNames := d.convPartyNames(r, convs)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.InboxPage(convs, partyNames, status, assignee).Render(r.Context(), w); err != nil {
		log.Printf("inbox: render: %v", err)
	}
}

// ── S06 Conversation Detail ────────────────────────────────────────────────────

func (d *Deps) handleConversationDetail(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")

	conv, err := d.ConvLinker.GetByID(r.Context(), convID)
	if err != nil || conv == nil {
		http.Error(w, "Không tìm thấy hội thoại", http.StatusNotFound)
		return
	}

	msgs, err := d.Conversations.GetMessages(r.Context(), convID)
	if err != nil {
		log.Printf("conv detail: get messages %s: %v", convID, err)
		msgs = []domain.Message{}
	}

	// Sidebar: resolve linked party name + 360 link.
	var partyName, partyLink string
	if conv.PartyID != nil {
		if p, err2 := d.Parties.GetByID(r.Context(), *conv.PartyID); err2 == nil && p != nil {
			partyName = p.DisplayName
			partyLink = "/customers/" + p.PartyID
		}
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ConversationDetailPage(conv, msgs, partyName, partyLink).Render(r.Context(), w); err != nil {
		log.Printf("conv detail: render %s: %v", convID, err)
	}
}

// ── M09 Assign Conversation ───────────────────────────────────────────────────

func (d *Deps) handleModalAssignConversation(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	conv, err := d.ConvLinker.GetByID(r.Context(), convID)
	if err != nil || conv == nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	users, _ := d.AppUsers.ListActive(r.Context())

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalAssignConversation(convID, conv, users).Render(r.Context(), w); err != nil {
		log.Printf("modal assign: render: %v", err)
	}
}

func (d *Deps) handleAssignConversation(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	assigneeID := strings.TrimSpace(r.FormValue("assignee_user_id"))
	if assigneeID == "" {
		http.Error(w, "assignee_user_id required", http.StatusBadRequest)
		return
	}
	if err := d.ConvWriter.AssignConversation(r.Context(), convID, assigneeID); err != nil {
		log.Printf("assign conv %s: %v", convID, err)
		http.Error(w, "failed to assign", http.StatusInternalServerError)
		return
	}
	w.Header().Set("HX-Trigger", `{"closeModal":true}`)
	w.WriteHeader(http.StatusOK)
}

// ── M10 Close Conversation ────────────────────────────────────────────────────

func (d *Deps) handleModalCloseConversation(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	conv, err := d.ConvLinker.GetByID(r.Context(), convID)
	if err != nil || conv == nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalCloseConversation(convID, conv).Render(r.Context(), w); err != nil {
		log.Printf("modal close conv: render: %v", err)
	}
}

func (d *Deps) handleCloseConversation(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	if err := d.ConvWriter.SetStatus(r.Context(), convID, "closed"); err != nil {
		log.Printf("close conv %s: %v", convID, err)
		http.Error(w, "failed to close", http.StatusInternalServerError)
		return
	}
	w.Header().Set("HX-Trigger", `{"closeModal":true}`)
	w.Header().Set("HX-Redirect", "/inbox/"+convID)
	w.WriteHeader(http.StatusOK)
}

// ── M11 Link Party to Conversation ───────────────────────────────────────────

func (d *Deps) handleModalLinkParty(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	conv, err := d.ConvLinker.GetByID(r.Context(), convID)
	if err != nil || conv == nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalLinkParty(convID, conv).Render(r.Context(), w); err != nil {
		log.Printf("modal link party: render: %v", err)
	}
}

// handleInboxPartySearch serves GET /inbox/{conversationID}/parties/search?q=… — live search fragment inside M11.
func (d *Deps) handleInboxPartySearch(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	q := strings.TrimSpace(r.URL.Query().Get("q"))
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if q == "" {
		_, _ = w.Write([]byte(`<div class="text-muted">Nhập tên hoặc SĐT để tìm...</div>`))
		return
	}
	partyIDs, err := d.Parties.SearchByName(r.Context(), q)
	if err != nil {
		log.Printf("inbox party search: %v", err)
		partyIDs = nil
	}
	parties := d.fetchPartiesByIDs(r, partyIDs)
	// Pass convID so each result row's hx-post targets the correct /inbox/{convID}/link-party URL.
	if err := templates.PartySearchResults(parties, convID).Render(r.Context(), w); err != nil {
		log.Printf("inbox party search: render: %v", err)
	}
}

func (d *Deps) handleLinkParty(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	partyID := strings.TrimSpace(r.FormValue("party_id"))
	if partyID == "" {
		http.Error(w, "party_id required", http.StatusBadRequest)
		return
	}
	if err := d.ConvLinker.LinkParty(r.Context(), convID, partyID); err != nil {
		log.Printf("link party conv %s party %s: %v", convID, partyID, err)
		http.Error(w, "failed to link party", http.StatusInternalServerError)
		return
	}
	// Full redirect so the sidebar re-renders with party info.
	w.Header().Set("HX-Redirect", "/inbox/"+convID)
	w.WriteHeader(http.StatusOK)
}

// ── M08 Log Activity (from S06) ───────────────────────────────────────────────

func (d *Deps) handleModalLogActivityConv(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	conv, err := d.ConvLinker.GetByID(r.Context(), convID)
	if err != nil || conv == nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	var partyID string
	if conv.PartyID != nil {
		partyID = *conv.PartyID
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalLogActivity(partyID, convID).Render(r.Context(), w); err != nil {
		log.Printf("modal log activity conv: render: %v", err)
	}
}

func (d *Deps) handleLogActivityOnConv(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "conversationID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	partyID := strings.TrimSpace(r.FormValue("party_id"))
	actType := strings.TrimSpace(r.FormValue("activity_type"))
	body := strings.TrimSpace(r.FormValue("body"))
	if partyID == "" || body == "" {
		http.Error(w, "party_id and body required", http.StatusBadRequest)
		return
	}
	if actType == "" {
		actType = "chat"
	}
	d.logActivityShared(w, r, partyID, actType, body, convID)
}

// ── shared helpers ────────────────────────────────────────────────────────────

// convPartyNames builds partyID → displayName for all conversations that have a party.
func (d *Deps) convPartyNames(r *http.Request, convs []domain.Conversation) map[string]string {
	out := make(map[string]string)
	for _, c := range convs {
		if c.PartyID == nil {
			continue
		}
		if _, seen := out[*c.PartyID]; seen {
			continue
		}
		if p, err := d.Parties.GetByID(r.Context(), *c.PartyID); err == nil && p != nil {
			out[*c.PartyID] = p.DisplayName
		}
	}
	return out
}

// fetchPartiesByIDs resolves a slice of party IDs to domain.Party values.
func (d *Deps) fetchPartiesByIDs(r *http.Request, ids []string) []domain.Party {
	out := make([]domain.Party, 0, len(ids))
	for _, id := range ids {
		if p, err := d.Parties.GetByID(r.Context(), id); err == nil && p != nil {
			out = append(out, *p)
		}
	}
	return out
}

// logActivityShared logs an activity via ActivityLogger; used from S06 and S03.
func (d *Deps) logActivityShared(w http.ResponseWriter, r *http.Request, partyID, actType, body, convID string) {
	a := &domain.Activity{
		PartyID:      partyID,
		ActivityType: actType,
		Body:         body,
		Channel:      "messenger",
	}
	if err := d.ActivityLog.LogActivity(r.Context(), a); err != nil {
		log.Printf("log activity party %s: %v", partyID, err)
		http.Error(w, "failed to log activity", http.StatusInternalServerError)
		return
	}
	w.Header().Set("HX-Trigger", `{"closeModal":true}`)
	if convID != "" {
		w.Header().Set("HX-Redirect", "/inbox/"+convID)
	}
	w.WriteHeader(http.StatusOK)
}

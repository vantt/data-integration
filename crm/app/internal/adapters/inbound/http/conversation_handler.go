// Package http — Conversation/inbox + Messenger ingest HTTP handlers.
// Auth: DEFERRED — LAN-trust only (per plan). FB webhook signature verification also deferred.
package http

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/messenger"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// InboxQuerier is the read interface for conversations.
type InboxQuerier interface {
	ListInbox(ctx context.Context, assigneeUserID, status string) ([]domain.Conversation, error)
	GetMessages(ctx context.Context, conversationID string) ([]domain.Message, error)
}

// InboxWriter covers conversation assignment and status changes.
type InboxWriter interface {
	AssignConversation(ctx context.Context, conversationID, assigneeUserID string) error
	SetStatus(ctx context.Context, conversationID, newStatus string) error
}

// MessageIngester accepts parsed chat messages.
type MessageIngester interface {
	IngestMessage(ctx context.Context, msg domain.ParsedMessage) error
}

// ConversationHandler wires inbox and ingest endpoints.
type ConversationHandler struct {
	querier  InboxQuerier
	writer   InboxWriter
	ingester MessageIngester
}

// NewConversationHandler constructs the handler.
func NewConversationHandler(q InboxQuerier, w InboxWriter, ing MessageIngester) *ConversationHandler {
	return &ConversationHandler{querier: q, writer: w, ingester: ing}
}

// RegisterRoutes mounts conversation routes on the given chi router.
func (h *ConversationHandler) RegisterRoutes(r chi.Router) {
	r.Get("/api/conversations", h.listInbox)
	r.Patch("/api/conversations/{id}", h.updateConversation)
	r.Get("/api/conversations/{id}/messages", h.listMessages)
	// Ingest endpoint: accepts a FB Messenger webhook payload for testing/dev.
	// Auth/signature verification: TODO when live FB token is wired.
	r.Post("/api/messenger/ingest", h.messengerIngest)
}

// GET /api/conversations?assignee=<user_id>&status=<status>
func (h *ConversationHandler) listInbox(w http.ResponseWriter, r *http.Request) {
	assignee := r.URL.Query().Get("assignee")
	status := r.URL.Query().Get("status")
	convs, err := h.querier.ListInbox(r.Context(), assignee, status)
	if err != nil {
		log.Printf("conversation handler: list inbox: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list conversations")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"conversations": convs})
}

// PATCH /api/conversations/{id}   body: {"assignee_user_id":"..."} or {"status":"closed"}
func (h *ConversationHandler) updateConversation(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "id")

	var body struct {
		AssigneeUserID *string `json:"assignee_user_id"`
		Status         *string `json:"status"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if body.AssigneeUserID != nil {
		if err := h.writer.AssignConversation(r.Context(), convID, *body.AssigneeUserID); err != nil {
			if domain.IsValidationError(err) {
				writeError(w, http.StatusBadRequest, err.Error())
			} else {
				log.Printf("conversation handler: assign %s: %v", convID, err)
				writeError(w, http.StatusInternalServerError, "operation failed")
			}
			return
		}
	}
	if body.Status != nil {
		if err := h.writer.SetStatus(r.Context(), convID, *body.Status); err != nil {
			if domain.IsValidationError(err) {
				writeError(w, http.StatusBadRequest, err.Error())
			} else {
				log.Printf("conversation handler: set status %s: %v", convID, err)
				writeError(w, http.StatusInternalServerError, "operation failed")
			}
			return
		}
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "conversation_id": convID})
}

// GET /api/conversations/{id}/messages
func (h *ConversationHandler) listMessages(w http.ResponseWriter, r *http.Request) {
	convID := chi.URLParam(r, "id")
	msgs, err := h.querier.GetMessages(r.Context(), convID)
	if err != nil {
		log.Printf("conversation handler: list messages %s: %v", convID, err)
		writeError(w, http.StatusInternalServerError, "failed to list messages")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"conversation_id": convID, "messages": msgs})
}

// POST /api/messenger/ingest
// Accepts a raw FB Messenger webhook payload JSON.
// Parses it and ingests each message event.
// Auth/FB signature verification: TODO — deferred until live token is available.
func (h *ConversationHandler) messengerIngest(w http.ResponseWriter, r *http.Request) {
	raw, err := io.ReadAll(io.LimitReader(r.Body, 1<<20)) // 1 MiB cap
	if err != nil {
		writeError(w, http.StatusBadRequest, "failed to read body")
		return
	}

	msgs, err := messenger.ParseWebhookPayload(raw)
	if err != nil {
		log.Printf("conversation handler: parse messenger payload: %v", err)
		writeError(w, http.StatusBadRequest, "invalid messenger payload")
		return
	}

	ingested, skipped := 0, 0
	for _, msg := range msgs {
		if err := h.ingester.IngestMessage(r.Context(), msg); err != nil {
			log.Printf("conversation handler: ingest message %s: %v", msg.ExternalMessageID, err)
			skipped++
			continue
		}
		ingested++
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"parsed":   len(msgs),
		"ingested": ingested,
		"skipped":  skipped,
	})
}

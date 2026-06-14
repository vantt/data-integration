// Package ports — outbound port for Conversation and Message persistence.
// Nothing here may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ConversationRepository persists and queries Conversation and Message records.
type ConversationRepository interface {
	// UpsertConversation inserts a new conversation or returns the existing one
	// matched by (channel, external_thread_id). Returns the conversation_id.
	UpsertConversation(ctx context.Context, c *domain.Conversation) (string, error)

	// GetConversationByID returns a conversation by primary key, or nil if not found.
	GetConversationByID(ctx context.Context, conversationID string) (*domain.Conversation, error)

	// UpdateConversation persists mutable fields: party_id, status, assignee_user_id,
	// last_message_at, unread_count, updated_at.
	UpdateConversation(ctx context.Context, c *domain.Conversation) error

	// InsertMessage inserts a message row; idempotent via UNIQUE(conversation_id, external_message_id).
	// Returns (messageID, inserted) — inserted=false means duplicate was skipped.
	InsertMessage(ctx context.Context, m *domain.Message) (string, bool, error)

	// ListConversations returns conversations filtered by assignee and/or status.
	// Empty string means "any" for that filter. Ordered by last_message_at DESC.
	ListConversations(ctx context.Context, assigneeUserID, status string) ([]domain.Conversation, error)

	// ListMessages returns messages for a conversation ordered by sent_at ASC.
	ListMessages(ctx context.Context, conversationID string) ([]domain.Message, error)

	// UpdateConversationOnMessage atomically advances last_message_at (take-max)
	// and increments unread_count by delta. Call only when a new message was inserted.
	// delta=1 for inbound, delta=0 for echo/outbound.
	UpdateConversationOnMessage(ctx context.Context, conversationID, sentAt string, unreadDelta int) error
}

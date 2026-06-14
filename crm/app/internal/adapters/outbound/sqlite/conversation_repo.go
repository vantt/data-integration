// Package sqlite — ConversationRepo: SQLite adapter implementing ports.ConversationRepository.
//
// UpsertConversation uses INSERT … ON CONFLICT DO NOTHING RETURNING.
// When the conflict fires, RETURNING yields no rows → sql.ErrNoRows.
// In that case we fall back to a GET by (channel, external_thread_id).
package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite/sqlcgen"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// ConversationRepo satisfies ports.ConversationRepository.
type ConversationRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewConversationRepo constructs a ConversationRepo.
func NewConversationRepo(db *DB) ports.ConversationRepository {
	return &ConversationRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

// UpsertConversation inserts a new conversation or returns the existing one's ID.
func (r *ConversationRepo) UpsertConversation(ctx context.Context, c *domain.Conversation) (string, error) {
	id, err := r.q.UpsertConversation(ctx, sqlcgen.UpsertConversationParams{
		ConversationID:   c.ConversationID,
		PartyID:          ptrToNullStr(c.PartyID),
		Channel:          c.Channel,
		ExternalThreadID: c.ExternalThreadID,
		PageID:           toNullString(c.PageID),
		Status:           c.Status,
		AssigneeUserID:   ptrToNullStr(c.AssigneeUserID),
		LastMessageAt:    ptrToNullStr(c.LastMessageAt),
		UnreadCount:      int64(c.UnreadCount),
		CreatedAt:        c.CreatedAt,
		UpdatedAt:        c.UpdatedAt,
	})
	if err == nil {
		return id, nil
	}
	// ON CONFLICT DO NOTHING → RETURNING yields no rows → ErrNoRows.
	// Fall back to fetching the existing row.
	if errors.Is(err, sql.ErrNoRows) {
		existing, getErr := r.q.GetConversationByChannelThread(ctx, sqlcgen.GetConversationByChannelThreadParams{
			Channel:          c.Channel,
			ExternalThreadID: c.ExternalThreadID,
		})
		if getErr != nil {
			return "", fmt.Errorf("conversation repo: fetch existing after conflict: %w", getErr)
		}
		return existing.ConversationID, nil
	}
	return "", fmt.Errorf("conversation repo: upsert conversation: %w", err)
}

// GetConversationByID returns a conversation by primary key, or nil if not found.
func (r *ConversationRepo) GetConversationByID(ctx context.Context, conversationID string) (*domain.Conversation, error) {
	row, err := r.q.GetConversationByID(ctx, conversationID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("conversation repo: get by id: %w", err)
	}
	c := convFromRow(row)
	return &c, nil
}

// UpdateConversation persists mutable conversation fields.
func (r *ConversationRepo) UpdateConversation(ctx context.Context, c *domain.Conversation) error {
	return r.q.UpdateConversation(ctx, sqlcgen.UpdateConversationParams{
		PartyID:        ptrToNullStr(c.PartyID),
		Status:         c.Status,
		AssigneeUserID: ptrToNullStr(c.AssigneeUserID),
		LastMessageAt:  ptrToNullStr(c.LastMessageAt),
		UnreadCount:    int64(c.UnreadCount),
		UpdatedAt:      c.UpdatedAt,
		ConversationID: c.ConversationID,
	})
}

// InsertMessage inserts a message; idempotent via UNIQUE(conversation_id, external_message_id).
// Returns (messageID, inserted=true) on success, or (existingID-or-"", false) on duplicate.
func (r *ConversationRepo) InsertMessage(ctx context.Context, m *domain.Message) (string, bool, error) {
	id, err := r.q.InsertMessage(ctx, sqlcgen.InsertMessageParams{
		MessageID:         m.MessageID,
		ConversationID:    m.ConversationID,
		ExternalMessageID: toNullString(m.ExternalMessageID),
		Direction:         toNullString(m.Direction),
		SenderRef:         toNullString(m.SenderRef),
		Body:              toNullString(m.Body),
		Attachments:       toNullString(m.Attachments),
		SentAt:            m.SentAt,
	})
	if err == nil {
		return id, true, nil
	}
	if errors.Is(err, sql.ErrNoRows) {
		// Duplicate — idempotent skip.
		return "", false, nil
	}
	return "", false, fmt.Errorf("conversation repo: insert message: %w", err)
}

// UpdateConversationOnMessage atomically advances last_message_at and increments
// unread_count by delta in a single SQL statement. Safe under concurrent writes.
func (r *ConversationRepo) UpdateConversationOnMessage(ctx context.Context, conversationID, sentAt string, unreadDelta int) error {
	sentAtNull := toNullString(sentAt)
	return r.q.UpdateConversationOnMessage(ctx, sqlcgen.UpdateConversationOnMessageParams{
		LastMessageAt:   sentAtNull,
		LastMessageAt_2: sentAtNull,
		UnreadCount:     int64(unreadDelta),
		ConversationID:  conversationID,
	})
}

// ListConversations returns conversations filtered by assignee and/or status, newest first.
// Uses composite-index query when both filters are set.
func (r *ConversationRepo) ListConversations(ctx context.Context, assigneeUserID, status string) ([]domain.Conversation, error) {
	var rows []sqlcgen.CrmConversation
	var err error

	switch {
	case assigneeUserID != "" && status != "":
		// Use the composite-index query to avoid fetching-all-then-filtering.
		rows, err = r.q.ListConversationsByAssigneeAndStatus(ctx, sqlcgen.ListConversationsByAssigneeAndStatusParams{
			AssigneeUserID: toNullString(assigneeUserID),
			Status:         status,
		})
		if err != nil {
			return nil, fmt.Errorf("conversation repo: list by assignee+status: %w", err)
		}
	case assigneeUserID != "":
		rows, err = r.q.ListConversationsByAssignee(ctx, toNullString(assigneeUserID))
		if err != nil {
			return nil, fmt.Errorf("conversation repo: list by assignee: %w", err)
		}
	case status != "":
		rows, err = r.q.ListConversationsByStatus(ctx, status)
		if err != nil {
			return nil, fmt.Errorf("conversation repo: list by status: %w", err)
		}
	default:
		rows, err = r.q.ListAllConversations(ctx)
		if err != nil {
			return nil, fmt.Errorf("conversation repo: list all: %w", err)
		}
	}

	out := make([]domain.Conversation, 0, len(rows))
	for _, row := range rows {
		out = append(out, convFromRow(row))
	}
	return out, nil
}

// ListMessages returns messages for a conversation ordered by sent_at ASC.
func (r *ConversationRepo) ListMessages(ctx context.Context, conversationID string) ([]domain.Message, error) {
	rows, err := r.q.ListMessagesByConversation(ctx, conversationID)
	if err != nil {
		return nil, fmt.Errorf("conversation repo: list messages: %w", err)
	}
	out := make([]domain.Message, 0, len(rows))
	for _, row := range rows {
		out = append(out, msgFromRow(row))
	}
	return out, nil
}

// ─── helpers ─────────────────────────────────────────────────────────────────

func ptrToNullStr(p *string) sql.NullString {
	if p == nil {
		return sql.NullString{}
	}
	return sql.NullString{String: *p, Valid: true}
}

func convFromRow(r sqlcgen.CrmConversation) domain.Conversation {
	c := domain.Conversation{
		ConversationID:   r.ConversationID,
		Channel:          r.Channel,
		ExternalThreadID: r.ExternalThreadID,
		PageID:           r.PageID.String,
		Status:           r.Status,
		UnreadCount:      int(r.UnreadCount),
		CreatedAt:        r.CreatedAt,
		UpdatedAt:        r.UpdatedAt,
	}
	if r.PartyID.Valid {
		s := r.PartyID.String
		c.PartyID = &s
	}
	if r.AssigneeUserID.Valid {
		s := r.AssigneeUserID.String
		c.AssigneeUserID = &s
	}
	if r.LastMessageAt.Valid {
		s := r.LastMessageAt.String
		c.LastMessageAt = &s
	}
	return c
}

func msgFromRow(r sqlcgen.CrmMessage) domain.Message {
	return domain.Message{
		MessageID:         r.MessageID,
		ConversationID:    r.ConversationID,
		ExternalMessageID: r.ExternalMessageID.String,
		Direction:         r.Direction.String,
		SenderRef:         r.SenderRef.String,
		Body:              r.Body.String,
		Attachments:       r.Attachments.String,
		SentAt:            r.SentAt,
	}
}

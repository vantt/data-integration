// Package web — WebConvRepo: thin adapter satisfying ConversationPartyLinker.
// Wraps the existing *sql.DB and sqlite.ConversationRepo to provide LinkParty
// and GetByID without adding a method to the shared ports.ConversationRepository.
package web

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// WebConvRepo satisfies ConversationPartyLinker.
// convRepo handles the main port operations; db is used for the direct update.
type WebConvRepo struct {
	convRepo ports.ConversationRepository
	db       *sql.DB
}

// NewWebConvRepo constructs a WebConvRepo.
func NewWebConvRepo(convRepo ports.ConversationRepository, db *sql.DB) ConversationPartyLinker {
	return &WebConvRepo{convRepo: convRepo, db: db}
}

// GetByID returns the conversation by ID.
func (r *WebConvRepo) GetByID(ctx context.Context, conversationID string) (*domain.Conversation, error) {
	conv, err := r.convRepo.GetConversationByID(ctx, conversationID)
	if err != nil {
		return nil, fmt.Errorf("web conv repo: get by id: %w", err)
	}
	return conv, nil
}

// LinkParty sets conversation.party_id to partyID.
func (r *WebConvRepo) LinkParty(ctx context.Context, conversationID, partyID string) error {
	const q = `UPDATE crm_conversation SET party_id = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE conversation_id = ?`
	res, err := r.db.ExecContext(ctx, q, partyID, conversationID)
	if err != nil {
		return fmt.Errorf("web conv repo: link party: %w", err)
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return fmt.Errorf("web conv repo: conversation %q not found", conversationID)
	}
	return nil
}

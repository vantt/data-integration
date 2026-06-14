// Package application — ConversationService: chat ingest + inbox management.
// Pure domain + ports only; no adapter imports.
package application

import (
	"context"
	"fmt"
	"log"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// ConversationService handles chat ingest and inbox operations.
type ConversationService struct {
	convRepo  ports.ConversationRepository
	partyRepo ports.PartyRepository
}

// NewConversationService constructs a ConversationService.
func NewConversationService(
	convRepo ports.ConversationRepository,
	partyRepo ports.PartyRepository,
) *ConversationService {
	return &ConversationService{convRepo: convRepo, partyRepo: partyRepo}
}

// IngestMessage processes one parsed chat message:
//  1. Upsert conversation by (channel, external_thread_id).
//  2. Insert message (idempotent on external_message_id).
//  3. Update last_message_at and unread_count.
//  4. Resolve psid → party: look up party_identity(type='psid', value=sender_psid).
//     If found, set conversation.party_id; otherwise leave null.
func (s *ConversationService) IngestMessage(ctx context.Context, msg domain.ParsedMessage) error {
	if msg.Channel == "" || msg.ExternalThreadID == "" {
		return domain.NewValidationError("channel and external_thread_id are required")
	}
	if msg.ExternalMessageID == "" {
		return domain.NewValidationError("external_message_id is required")
	}
	if msg.SentAt == "" {
		return domain.NewValidationError("sent_at is required")
	}

	now := utcNow()

	// Step 1: upsert conversation (get or create).
	conv := &domain.Conversation{
		ConversationID:   uuid.New().String(),
		Channel:          msg.Channel,
		ExternalThreadID: msg.ExternalThreadID,
		PageID:           msg.PageID,
		Status:           "open",
		UnreadCount:      0,
		CreatedAt:        now,
		UpdatedAt:        now,
	}
	convID, err := s.convRepo.UpsertConversation(ctx, conv)
	if err != nil {
		return fmt.Errorf("conversation service: upsert conversation: %w", err)
	}

	// Step 2: insert message (idempotent).
	message := &domain.Message{
		MessageID:         uuid.New().String(),
		ConversationID:    convID,
		ExternalMessageID: msg.ExternalMessageID,
		Direction:         msg.Direction,
		SenderRef:         msg.SenderRef,
		Body:              msg.Body,
		Attachments:       msg.Attachments,
		SentAt:            msg.SentAt,
	}
	_, inserted, err := s.convRepo.InsertMessage(ctx, message)
	if err != nil {
		return fmt.Errorf("conversation service: insert message: %w", err)
	}
	if !inserted {
		// Duplicate message — nothing more to do.
		return nil
	}

	// Step 3: atomic update of last_message_at (take-max) and unread_count delta.
	// unreadDelta=1 for inbound, 0 for echo/outbound — avoids double-increment on re-ingest
	// because InsertMessage already returned inserted=false (not reached here) for duplicates.
	unreadDelta := 0
	if msg.Direction == "in" {
		unreadDelta = 1
	}
	if err := s.convRepo.UpdateConversationOnMessage(ctx, convID, msg.SentAt, unreadDelta); err != nil {
		return fmt.Errorf("conversation service: update conversation on message: %w", err)
	}

	// Step 4: resolve psid → party (Messenger-specific).
	// Reload to check current party_id; only update if not yet linked.
	existing, err := s.convRepo.GetConversationByID(ctx, convID)
	if err != nil {
		return fmt.Errorf("conversation service: reload conversation for party lookup: %w", err)
	}
	if existing == nil {
		return fmt.Errorf("conversation service: conversation %s not found after upsert", convID)
	}

	// Use sender_ref for psid lookup (customer psid for inbound, page id for echo).
	// For inbound messages, sender_ref == the customer psid.
	psidRef := msg.SenderRef
	if msg.Direction == "in" {
		psidRef = msg.SenderRef
	} else {
		// For echo/outbound, ExternalThreadID IS the customer psid (set by parser).
		psidRef = msg.ExternalThreadID
	}

	if existing.PartyID == nil && psidRef != "" {
		party, lookupErr := s.partyRepo.FindByIdentity(ctx, "psid", psidRef)
		if lookupErr != nil {
			log.Printf("conversation service: psid lookup %s: %v", psidRef, lookupErr)
		} else if party != nil {
			existing.PartyID = &party.PartyID
			// updated_at is owned by trg_conversation_touch trigger.
			if err := s.convRepo.UpdateConversation(ctx, existing); err != nil {
				return fmt.Errorf("conversation service: update conversation party: %w", err)
			}
		}
	}
	return nil
}

// ListInbox returns conversations filtered by optional assignee and/or status.
func (s *ConversationService) ListInbox(ctx context.Context, assigneeUserID, status string) ([]domain.Conversation, error) {
	convs, err := s.convRepo.ListConversations(ctx, assigneeUserID, status)
	if err != nil {
		return nil, fmt.Errorf("conversation service: list inbox: %w", err)
	}
	if convs == nil {
		convs = []domain.Conversation{}
	}
	return convs, nil
}

// AssignConversation assigns a conversation to a staff user.
func (s *ConversationService) AssignConversation(ctx context.Context, conversationID, assigneeUserID string) error {
	conv, err := s.convRepo.GetConversationByID(ctx, conversationID)
	if err != nil {
		return fmt.Errorf("conversation service: assign: %w", err)
	}
	if conv == nil {
		return domain.NewValidationError(fmt.Sprintf("conversation %q not found", conversationID))
	}
	conv.AssigneeUserID = &assigneeUserID
	// updated_at is owned by trg_conversation_touch trigger — no app-side stamp needed.
	return s.convRepo.UpdateConversation(ctx, conv)
}

// SetStatus transitions a conversation's status (open|pending|closed).
func (s *ConversationService) SetStatus(ctx context.Context, conversationID, newStatus string) error {
	if !domain.IsValidConversationStatus(newStatus) {
		return domain.NewValidationError(fmt.Sprintf("invalid conversation status %q", newStatus))
	}
	conv, err := s.convRepo.GetConversationByID(ctx, conversationID)
	if err != nil {
		return fmt.Errorf("conversation service: set status: %w", err)
	}
	if conv == nil {
		return domain.NewValidationError(fmt.Sprintf("conversation %q not found", conversationID))
	}
	if err := domain.CanTransitionConvTo(conv.Status, newStatus); err != nil {
		return domain.NewValidationError(err.Error())
	}
	conv.Status = newStatus
	// updated_at is owned by trg_conversation_touch trigger — no app-side stamp needed.
	return s.convRepo.UpdateConversation(ctx, conv)
}

// GetMessages returns all messages in a conversation ordered by sent_at ASC.
func (s *ConversationService) GetMessages(ctx context.Context, conversationID string) ([]domain.Message, error) {
	msgs, err := s.convRepo.ListMessages(ctx, conversationID)
	if err != nil {
		return nil, fmt.Errorf("conversation service: get messages: %w", err)
	}
	if msgs == nil {
		msgs = []domain.Message{}
	}
	return msgs, nil
}

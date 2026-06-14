// Package domain — Conversation and Message entities.
// A Conversation is a thread of messages on an external channel (Messenger, Zalo, Shopee).
// No adapter imports allowed here.
package domain

import "fmt"

// Conversation tracks a chat thread between a customer and the shop.
// party_id is nullable until the external sender (psid) is resolved to a CRM party.
type Conversation struct {
	ConversationID   string  // UUID
	PartyID          *string // FK → crm_party (nullable)
	Channel          string  // messenger|shopee|zalo
	ExternalThreadID string  // psid (Messenger) / buyer id (Shopee) / user id (Zalo)
	PageID           string  // FB page / Shopee shop / Zalo OA identifier
	Status           string  // open|pending|closed
	AssigneeUserID   *string // FK → crm_app_user nullable
	LastMessageAt    *string // UTC ISO-8601 nullable
	UnreadCount      int
	CreatedAt        string // UTC ISO-8601
	UpdatedAt        string // UTC ISO-8601
}

// Message is one inbound or outbound message within a conversation.
type Message struct {
	MessageID         string  // UUID
	ConversationID    string  // FK → crm_conversation
	ExternalMessageID string  // channel-native message id (idempotency key)
	Direction         string  // in|out
	SenderRef         string  // psid, page_id, or staff identifier
	Body              string
	Attachments       string  // JSON array (TEXT column); empty string = no attachments
	SentAt            string  // UTC ISO-8601
}

// ValidConversationStatuses lists accepted status values.
var ValidConversationStatuses = []string{"open", "pending", "closed"}

// IsValidConversationStatus returns true when s is an accepted conversation status.
func IsValidConversationStatus(s string) bool {
	for _, v := range ValidConversationStatuses {
		if v == s {
			return true
		}
	}
	return false
}

// allowedConvTransitions maps current status → reachable next statuses.
var allowedConvTransitions = map[string][]string{
	"open":    {"pending", "closed"},
	"pending": {"open", "closed"},
	"closed":  {"open"},
}

// CanTransitionConvTo returns nil when current → next is a valid conversation transition.
func CanTransitionConvTo(current, next string) error {
	if current == next {
		return nil
	}
	targets, ok := allowedConvTransitions[current]
	if !ok {
		return fmt.Errorf("conversation: unknown current status %q", current)
	}
	for _, t := range targets {
		if t == next {
			return nil
		}
	}
	return fmt.Errorf("conversation: transition %q → %q is not allowed", current, next)
}

// ParsedMessage is the normalised representation produced by a chat-source adapter
// (e.g. MessengerAdapter) before it is passed to ConversationService.IngestMessage.
// This is the seam between inbound adapters and the application layer.
type ParsedMessage struct {
	Channel           string // messenger|shopee|zalo
	ExternalThreadID  string // psid (sender id for Messenger)
	PageID            string // FB page / shop / OA id
	ExternalMessageID string // channel-native message id
	Direction         string // in|out
	SenderRef         string // who sent (psid or page_id)
	Body              string
	Attachments       string  // JSON array or empty string
	SentAt            string  // UTC ISO-8601
}

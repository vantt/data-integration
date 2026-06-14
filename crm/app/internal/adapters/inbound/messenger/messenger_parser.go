// Package messenger — inbound adapter that parses FB Messenger webhook payloads.
//
// Scope (v1): parse payload JSON → []domain.ParsedMessage.
// Live FB Graph API fetch is OUT OF SCOPE for v1 (no token on this host).
//
// TODO (live integration): To enable real-time ingest, implement a transport layer
// that either:
//   a) Receives the FB webhook POST (verify token + X-Hub-Signature-256 check), or
//   b) Polls FB Graph API: GET /{page-id}/conversations?fields=messages{...}&access_token=TOKEN
// Both paths produce the same raw JSON that ParseWebhookPayload already handles.
// Wire the transport to call ParseWebhookPayload, then ConversationService.IngestMessage
// for each returned ParsedMessage. The token/transport plumbing belongs in cmd/server
// or a dedicated crm/sync/ingest_messenger.go (Python or Go) — not here.
//
// Hexagonal position: inbound adapter (no imports of sqlite or application packages).
package messenger

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// WebhookPayload is the top-level FB Messenger webhook body.
// FB sends: {"object":"page","entry":[{"id":"<page_id>","messaging":[...]}]}
type WebhookPayload struct {
	Object string        `json:"object"`
	Entry  []EntryObject `json:"entry"`
}

// EntryObject represents one page entry in the webhook.
type EntryObject struct {
	ID        string            `json:"id"` // FB page id
	Messaging []MessagingObject `json:"messaging"`
}

// MessagingObject represents one send/receive event.
type MessagingObject struct {
	Sender    ParticipantRef `json:"sender"`
	Recipient ParticipantRef `json:"recipient"`
	Timestamp int64          `json:"timestamp"` // Unix ms
	Message   *MessageEvent  `json:"message,omitempty"`
}

// ParticipantRef holds an PSID or page id.
type ParticipantRef struct {
	ID string `json:"id"`
}

// MessageEvent is the nested message object within a MessagingObject.
type MessageEvent struct {
	MID         string       `json:"mid"`
	Text        string       `json:"text,omitempty"`
	IsEcho      bool         `json:"is_echo,omitempty"`
	Attachments []Attachment `json:"attachments,omitempty"`
}

// Attachment is a FB Messenger attachment (image, video, file, etc.).
type Attachment struct {
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload,omitempty"`
}

// ParseWebhookPayload parses a raw FB Messenger webhook JSON body and returns
// one domain.ParsedMessage per message event (inbound and echo/outbound).
//
// Only message events (messaging[].message != nil) are processed; delivery/read
// receipts and other event types are silently skipped.
//
// Thread key: always keyed on the customer psid. For echo events (page-sent),
// sender.id is the page_id and the customer psid is in recipient.id.
// Direction: "in" for customer→page, "out" for page→customer (echo).
//
// Timestamps: events with ms <= 0 are skipped with a logged reason rather than
// using time.Now() as a fallback, which would produce incorrect data.
func ParseWebhookPayload(raw []byte) ([]domain.ParsedMessage, error) {
	var payload WebhookPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("messenger parser: unmarshal payload: %w", err)
	}

	var out []domain.ParsedMessage
	for _, entry := range payload.Entry {
		pageID := entry.ID
		for _, ev := range entry.Messaging {
			if ev.Message == nil {
				continue // skip delivery/read receipts
			}
			mid := ev.Message.MID
			if mid == "" {
				continue // malformed; skip
			}

			// Reject bad timestamps rather than silently using time.Now().
			sentAt, err := msToUTC(ev.Timestamp)
			if err != nil {
				fmt.Printf("messenger parser: skipping mid=%s: %v\n", mid, err)
				continue
			}

			// Determine direction and thread key.
			// Echo events have sender.id == pageID (or is_echo flag set).
			// The conversation thread is always keyed on the CUSTOMER psid.
			isEcho := ev.Message.IsEcho || ev.Sender.ID == pageID
			direction := "in"
			threadPSID := ev.Sender.ID
			senderRef := ev.Sender.ID
			if isEcho {
				direction = "out"
				// For page-sent/echo, the customer psid is in recipient.id.
				threadPSID = ev.Recipient.ID
				senderRef = ev.Sender.ID // keep actual sender (page id)
			}

			// Serialise attachments as JSON array string (empty string when none).
			attachments := ""
			if len(ev.Message.Attachments) > 0 {
				b, _ := json.Marshal(ev.Message.Attachments)
				attachments = string(b)
			}

			out = append(out, domain.ParsedMessage{
				Channel:           "messenger",
				ExternalThreadID:  threadPSID, // always the customer psid
				PageID:            pageID,
				ExternalMessageID: mid,
				Direction:         direction,
				SenderRef:         senderRef,
				Body:              ev.Message.Text,
				Attachments:       attachments,
				SentAt:            sentAt,
			})
		}
	}
	return out, nil
}

// msToUTC converts a Unix millisecond timestamp to UTC ISO-8601 string.
// Returns an error for ms <= 0 rather than falling back to time.Now(),
// so callers can skip malformed events instead of recording wrong timestamps.
func msToUTC(ms int64) (string, error) {
	if ms <= 0 {
		return "", fmt.Errorf("invalid timestamp ms=%d (must be > 0)", ms)
	}
	return time.UnixMilli(ms).UTC().Format("2006-01-02T15:04:05.000Z"), nil
}

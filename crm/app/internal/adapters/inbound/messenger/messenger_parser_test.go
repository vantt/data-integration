// Package messenger — unit tests for ParseWebhookPayload.
package messenger

import (
	"strings"
	"testing"
)

// TestParser_EchoMessage_ThreadKeyIsRecipient verifies that for an echo event
// (sender.id == pageID / is_echo=true) the ExternalThreadID is set to the
// customer psid (recipient.id) and direction is "out".
func TestParser_EchoMessage_ThreadKeyIsRecipient(t *testing.T) {
	// Echo: sender=pageID, recipient=customerPSID, is_echo=true
	payload := `{
		"object": "page",
		"entry": [{
			"id": "PAGE123",
			"messaging": [{
				"sender":    {"id": "PAGE123"},
				"recipient": {"id": "CUST456"},
				"timestamp": 1718323200000,
				"message": {
					"mid": "echo.001",
					"text": "Cảm ơn bạn!",
					"is_echo": true
				}
			}]
		}]
	}`
	msgs, err := ParseWebhookPayload([]byte(payload))
	if err != nil {
		t.Fatalf("parse error: %v", err)
	}
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message, got %d", len(msgs))
	}
	msg := msgs[0]
	if msg.ExternalThreadID != "CUST456" {
		t.Errorf("ExternalThreadID = %q; want CUST456 (customer psid)", msg.ExternalThreadID)
	}
	if msg.Direction != "out" {
		t.Errorf("Direction = %q; want out", msg.Direction)
	}
	if msg.SenderRef != "PAGE123" {
		t.Errorf("SenderRef = %q; want PAGE123 (actual sender)", msg.SenderRef)
	}
}

// TestParser_EchoMessage_SenderEqualsPageID verifies the same echo logic when
// is_echo is not set but sender.id == pageID (older Messenger webhook format).
func TestParser_EchoMessage_SenderEqualsPageID(t *testing.T) {
	payload := `{
		"object": "page",
		"entry": [{
			"id": "PAGE999",
			"messaging": [{
				"sender":    {"id": "PAGE999"},
				"recipient": {"id": "CUST111"},
				"timestamp": 1718323200000,
				"message": {"mid": "out.001", "text": "Xin chào"}
			}]
		}]
	}`
	msgs, err := ParseWebhookPayload([]byte(payload))
	if err != nil {
		t.Fatalf("parse error: %v", err)
	}
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message, got %d", len(msgs))
	}
	msg := msgs[0]
	if msg.ExternalThreadID != "CUST111" {
		t.Errorf("ExternalThreadID = %q; want CUST111", msg.ExternalThreadID)
	}
	if msg.Direction != "out" {
		t.Errorf("Direction = %q; want out", msg.Direction)
	}
}

// TestParser_InboundMessage_ThreadKeyIsSender verifies that for a normal inbound
// message (sender=customer), ExternalThreadID == sender.id and direction == "in".
func TestParser_InboundMessage_ThreadKeyIsSender(t *testing.T) {
	payload := `{
		"object": "page",
		"entry": [{
			"id": "PAGE999",
			"messaging": [{
				"sender":    {"id": "CUST111"},
				"recipient": {"id": "PAGE999"},
				"timestamp": 1718323200000,
				"message": {"mid": "in.001", "text": "Xin chào shop"}
			}]
		}]
	}`
	msgs, err := ParseWebhookPayload([]byte(payload))
	if err != nil {
		t.Fatalf("parse error: %v", err)
	}
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message, got %d", len(msgs))
	}
	msg := msgs[0]
	if msg.ExternalThreadID != "CUST111" {
		t.Errorf("ExternalThreadID = %q; want CUST111", msg.ExternalThreadID)
	}
	if msg.Direction != "in" {
		t.Errorf("Direction = %q; want in", msg.Direction)
	}
}

// TestParser_MalformedJSON_ReturnsError verifies that invalid JSON returns an error.
func TestParser_MalformedJSON_ReturnsError(t *testing.T) {
	_, err := ParseWebhookPayload([]byte(`{not valid json`))
	if err == nil {
		t.Fatal("expected error for malformed JSON, got nil")
	}
}

// TestParser_BadTimestamp_SkippedOrRejected verifies that an event with timestamp<=0
// is skipped (not returned) rather than using time.Now() as fallback.
func TestParser_BadTimestamp_SkippedOrRejected(t *testing.T) {
	payload := `{
		"object": "page",
		"entry": [{
			"id": "PAGE1",
			"messaging": [
				{
					"sender":    {"id": "CUST1"},
					"recipient": {"id": "PAGE1"},
					"timestamp": 0,
					"message": {"mid": "bad.ts", "text": "no timestamp"}
				},
				{
					"sender":    {"id": "CUST1"},
					"recipient": {"id": "PAGE1"},
					"timestamp": 1718323200000,
					"message": {"mid": "good.ts", "text": "valid"}
				}
			]
		}]
	}`
	msgs, err := ParseWebhookPayload([]byte(payload))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// The bad-timestamp event must be skipped; only the valid one returned.
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message (bad-ts skipped), got %d", len(msgs))
	}
	if msgs[0].ExternalMessageID != "good.ts" {
		t.Errorf("ExternalMessageID = %q; want good.ts", msgs[0].ExternalMessageID)
	}
}

// TestParser_Attachment_ParsedCorrectly verifies that a message with no text
// but attachments is returned with a non-empty Attachments JSON string.
func TestParser_Attachment_ParsedCorrectly(t *testing.T) {
	payload := `{
		"object": "page",
		"entry": [{
			"id": "PAGE1",
			"messaging": [{
				"sender":    {"id": "CUST1"},
				"recipient": {"id": "PAGE1"},
				"timestamp": 1718323200000,
				"message": {
					"mid": "att.001",
					"attachments": [
						{"type": "image", "payload": {"url": "https://example.com/img.jpg"}}
					]
				}
			}]
		}]
	}`
	msgs, err := ParseWebhookPayload([]byte(payload))
	if err != nil {
		t.Fatalf("parse error: %v", err)
	}
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message, got %d", len(msgs))
	}
	msg := msgs[0]
	if msg.Body != "" {
		t.Errorf("Body = %q; want empty (attachment-only message)", msg.Body)
	}
	if msg.Attachments == "" {
		t.Error("Attachments should be non-empty JSON string for image message")
	}
	if !strings.Contains(msg.Attachments, "image") {
		t.Errorf("Attachments = %q; expected to contain type 'image'", msg.Attachments)
	}
}

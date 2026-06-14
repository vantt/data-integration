// Package sqlite — Phase 05 integration tests.
// All tests use a real temp SQLite DB with migrations 0001-0004 applied; no mocks.
// Chat ingest tests are driven by FIXTURE Messenger payloads (no live FB token).
package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"path/filepath"
	"testing"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/messenger"
	"github.com/vantt/data-integration/crm/app/internal/application"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── helpers ─────────────────────────────────────────────────────────────────

func buildActivitySvc(db *DB) *application.ActivityService {
	return application.NewActivityService(NewActivityRepo(db))
}

func buildTaskSvc(db *DB) *application.TaskService {
	partyRepo := NewPartyRepo(db)
	cacheRepo := NewCacheRepo(db)
	return application.NewTaskService(NewTaskRepo(db), partyRepo, cacheRepo)
}

func buildConvSvc(db *DB) *application.ConversationService {
	return application.NewConversationService(NewConversationRepo(db), NewPartyRepo(db))
}

// seedPartyWithPSID creates a party and registers a psid identity for it.
func seedPartyWithPSID(t *testing.T, db *DB, psid string) string {
	t.Helper()
	ctx := context.Background()
	party := makeParty("FB User", "", "")
	partyRepo := NewPartyRepo(db)
	if err := partyRepo.Create(ctx, party); err != nil {
		t.Fatalf("seed party: %v", err)
	}
	id := &domain.PartyIdentity{
		IdentityID:    uuid.New().String(),
		PartyID:       party.PartyID,
		SourceSystem:  "messenger",
		IdentityType:  "psid",
		IdentityValue: psid,
		Confidence:    1.0,
		CreatedAt:     utcTestNow(),
	}
	if err := partyRepo.UpsertIdentity(ctx, id); err != nil {
		t.Fatalf("seed psid identity: %v", err)
	}
	return party.PartyID
}

// openTestDBWithDir is like openTestDB but also returns the data directory path.
// Used when tests need to seed cache.db directly (writable path, not via ATTACH).
func openTestDBWithDir(t *testing.T) (*DB, string, func()) {
	t.Helper()
	dir := t.TempDir()
	db, err := Open(dir)
	if err != nil {
		t.Fatalf("open test db: %v", err)
	}
	if err := MigrateUp(db); err != nil {
		_ = db.Close()
		t.Fatalf("migrate up: %v", err)
	}
	return db, dir, func() {
		_ = db.Close()
	}
}

// seedActionQueueInCache seeds wh_action_queue directly into cache.db by opening
// a separate writable connection to the cache file.
// cache.db is ATTACHed to the main crm.db conn as read-only, so writes must go
// through a dedicated writable connection opened directly on the file path.
func seedActionQueueInCache(t *testing.T, dataDir string, actions []domain.ActionQueueItem) {
	t.Helper()
	ctx := context.Background()

	cacheDSN := "file:" + filepath.ToSlash(filepath.Join(dataDir, "cache.db"))
	cacheConn, err := sql.Open("sqlite", cacheDSN)
	if err != nil {
		t.Fatalf("open cache.db for seeding: %v", err)
	}
	defer cacheConn.Close()

	_, err = cacheConn.ExecContext(ctx, `
		CREATE TABLE IF NOT EXISTS wh_action_queue (
			action_id          TEXT PRIMARY KEY,
			customer_key       TEXT NOT NULL,
			action_type        TEXT NOT NULL,
			rationale_vi       TEXT,
			value_at_stake_vnd INTEGER,
			priority           INTEGER DEFAULT 0,
			generated_date     TEXT,
			refreshed_at       TEXT
		)`)
	if err != nil {
		t.Fatalf("create wh_action_queue in cache.db: %v", err)
	}

	for _, a := range actions {
		_, err := cacheConn.ExecContext(ctx,
			`INSERT OR REPLACE INTO wh_action_queue
				(action_id, customer_key, action_type, rationale_vi, value_at_stake_vnd, priority, generated_date, refreshed_at)
			 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			a.ActionID, a.CustomerKey, a.ActionType, a.RationaleVI,
			a.ValueAtStakeVND, a.Priority, a.GeneratedDate, a.RefreshedAt,
		)
		if err != nil {
			t.Fatalf("insert action %s: %v", a.ActionID, err)
		}
	}
}

// ─── Activity timeline ────────────────────────────────────────────────────────

func TestActivityTimeline_OrderedNewestFirst(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildActivitySvc(db)

	// Log two activities with explicit occurred_at to test ordering.
	acts := []struct {
		atype      string
		occurredAt string
	}{
		{"call", "2026-01-01T08:00:00.000Z"},
		{"note", "2026-01-02T09:00:00.000Z"},
		{"visit", "2026-01-03T10:00:00.000Z"},
	}
	for _, a := range acts {
		if err := svc.LogActivity(ctx, &domain.Activity{
			PartyID:      partyID,
			ActivityType: a.atype,
			OccurredAt:   a.occurredAt,
		}); err != nil {
			t.Fatalf("log activity %s: %v", a.atype, err)
		}
	}

	timeline, err := svc.ListTimeline(ctx, partyID)
	if err != nil {
		t.Fatalf("list timeline: %v", err)
	}
	if len(timeline) != 3 {
		t.Fatalf("expected 3 activities, got %d", len(timeline))
	}
	// Newest first: visit > note > call.
	if timeline[0].ActivityType != "visit" {
		t.Errorf("first activity should be 'visit', got %q", timeline[0].ActivityType)
	}
	if timeline[2].ActivityType != "call" {
		t.Errorf("last activity should be 'call', got %q", timeline[2].ActivityType)
	}
}

func TestActivity_InvalidType_Rejected(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	_, partyID := seedUserAndParty(t, db)
	svc := buildActivitySvc(db)

	err := svc.LogActivity(ctx, &domain.Activity{
		PartyID:      partyID,
		ActivityType: "teleport", // invalid
	})
	if err == nil {
		t.Fatal("expected error for invalid activity_type, got nil")
	}
}

// ─── Task status transitions ──────────────────────────────────────────────────

func TestTaskStatusTransitions(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildTaskSvc(db)

	t.Run("open→doing→done", func(t *testing.T) {
		task := &domain.Task{Title: "Follow-up call"}
		if err := svc.CreateTask(ctx, task); err != nil {
			t.Fatalf("create task: %v", err)
		}
		if err := svc.TransitionStatus(ctx, task.TaskID, "doing"); err != nil {
			t.Fatalf("open→doing: %v", err)
		}
		if err := svc.TransitionStatus(ctx, task.TaskID, "done"); err != nil {
			t.Fatalf("doing→done: %v", err)
		}
		got, _ := svc.GetTask(ctx, task.TaskID)
		if got.Status != "done" {
			t.Errorf("status = %q; want done", got.Status)
		}
		if got.CompletedAt == nil {
			t.Error("completed_at should be set when done")
		}
	})

	t.Run("invalid transition open→done skips doing", func(t *testing.T) {
		// open→done IS allowed per domain rules.
		task := &domain.Task{Title: "Direct close"}
		if err := svc.CreateTask(ctx, task); err != nil {
			t.Fatalf("create task: %v", err)
		}
		if err := svc.TransitionStatus(ctx, task.TaskID, "done"); err != nil {
			t.Errorf("open→done should be allowed, got: %v", err)
		}
	})

	t.Run("cancelled→doing is forbidden", func(t *testing.T) {
		task := &domain.Task{Title: "Cancelled task"}
		if err := svc.CreateTask(ctx, task); err != nil {
			t.Fatalf("create task: %v", err)
		}
		_ = svc.TransitionStatus(ctx, task.TaskID, "cancelled")
		err := svc.TransitionStatus(ctx, task.TaskID, "doing")
		if err == nil {
			t.Fatal("expected error for cancelled→doing, got nil")
		}
	})
}

// ─── GenerateTasksFromActionQueue ─────────────────────────────────────────────

func TestGenerateTasksFromActionQueue_CacheEmpty(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	// No wh_action_queue table → graceful empty, no error.
	svc := buildTaskSvc(db)
	n, err := svc.GenerateTasksFromActionQueue(context.Background())
	if err != nil {
		t.Fatalf("expected no error when cache empty, got: %v", err)
	}
	if n != 0 {
		t.Errorf("expected 0 tasks, got %d", n)
	}
}

func TestGenerateTasksFromActionQueue_CreatesAndDeduplicates(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()

	// Seed a party with a sapo_customer identity matching the action's customer_key.
	party := makeParty("Test Customer", "+84900000001", "")
	partyRepo := NewPartyRepo(db)
	if err := partyRepo.Create(ctx, party); err != nil {
		t.Fatalf("seed party: %v", err)
	}
	customerKey := "CUST-001"
	identity := &domain.PartyIdentity{
		IdentityID:    uuid.New().String(),
		PartyID:       party.PartyID,
		SourceSystem:  "sapo",
		IdentityType:  "sapo_customer",
		IdentityValue: customerKey,
		Confidence:    1.0,
		CreatedAt:     utcTestNow(),
	}
	if err := partyRepo.UpsertIdentity(ctx, identity); err != nil {
		t.Fatalf("seed identity: %v", err)
	}

	// Seed action queue with 2 actions; one matches party, one does not.
	// Write directly to cache.db (writable path) — not via the read-only ATTACH.
	actions := []domain.ActionQueueItem{
		{ActionID: "ACT-001", CustomerKey: customerKey, ActionType: "WIN_BACK", RationaleVI: "Khách lâu không mua", Priority: 1},
		{ActionID: "ACT-002", CustomerKey: "CUST-UNKNOWN", ActionType: "CALL_NOW", RationaleVI: "Gọi ngay", Priority: 2},
	}
	seedActionQueueInCache(t, dataDir, actions)

	svc := buildTaskSvc(db)

	// First run: should create 2 tasks.
	n, err := svc.GenerateTasksFromActionQueue(ctx)
	if err != nil {
		t.Fatalf("first generate: %v", err)
	}
	if n != 2 {
		t.Errorf("expected 2 tasks created, got %d", n)
	}

	// Verify party_id linked for known customer.
	tasks, err := svc.ListTasks(ctx, "", "open")
	if err != nil {
		t.Fatalf("list tasks: %v", err)
	}
	var linkedTask *domain.Task
	for i := range tasks {
		if tasks[i].SourceRef != nil && *tasks[i].SourceRef == "ACT-001" {
			linkedTask = &tasks[i]
			break
		}
	}
	if linkedTask == nil {
		t.Fatal("task for ACT-001 not found")
	}
	if linkedTask.PartyID == nil || *linkedTask.PartyID != party.PartyID {
		t.Errorf("ACT-001 task party_id = %v; want %s", linkedTask.PartyID, party.PartyID)
	}

	// Verify unknown customer task has nil party_id.
	var unknownTask *domain.Task
	for i := range tasks {
		if tasks[i].SourceRef != nil && *tasks[i].SourceRef == "ACT-002" {
			unknownTask = &tasks[i]
			break
		}
	}
	if unknownTask == nil {
		t.Fatal("task for ACT-002 not found")
	}
	if unknownTask.PartyID != nil {
		t.Errorf("ACT-002 task should have nil party_id (unknown customer), got %v", *unknownTask.PartyID)
	}

	// Second run: must be idempotent — 0 new tasks.
	n2, err := svc.GenerateTasksFromActionQueue(ctx)
	if err != nil {
		t.Fatalf("second generate: %v", err)
	}
	if n2 != 0 {
		t.Errorf("expected 0 tasks on second run (idempotent), got %d", n2)
	}
}

// ─── Chat ingest: Messenger fixture ──────────────────────────────────────────

// messengerFixture is a realistic FB Messenger webhook payload with 2 inbound messages
// from a customer (psid=12345) to page (page_id=99999).
const messengerFixture = `{
  "object": "page",
  "entry": [{
    "id": "99999",
    "messaging": [
      {
        "sender": {"id": "12345"},
        "recipient": {"id": "99999"},
        "timestamp": 1718323200000,
        "message": {"mid": "mid.001", "text": "Xin chào, tôi muốn hỏi về sản phẩm"}
      },
      {
        "sender": {"id": "12345"},
        "recipient": {"id": "99999"},
        "timestamp": 1718323260000,
        "message": {"mid": "mid.002", "text": "Giá bao nhiêu?"}
      }
    ]
  }]
}`

func TestMessengerIngest_CreatesConversationAndMessages(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildConvSvc(db)

	msgs, err := messenger.ParseWebhookPayload([]byte(messengerFixture))
	if err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	if len(msgs) != 2 {
		t.Fatalf("expected 2 parsed messages, got %d", len(msgs))
	}

	for _, msg := range msgs {
		if err := svc.IngestMessage(ctx, msg); err != nil {
			t.Fatalf("ingest message %s: %v", msg.ExternalMessageID, err)
		}
	}

	// Conversation should exist.
	convs, err := svc.ListInbox(ctx, "", "")
	if err != nil {
		t.Fatalf("list inbox: %v", err)
	}
	if len(convs) != 1 {
		t.Fatalf("expected 1 conversation, got %d", len(convs))
	}
	conv := convs[0]
	if conv.Channel != "messenger" {
		t.Errorf("channel = %q; want messenger", conv.Channel)
	}
	if conv.ExternalThreadID != "12345" {
		t.Errorf("external_thread_id = %q; want 12345", conv.ExternalThreadID)
	}
	if conv.UnreadCount != 2 {
		t.Errorf("unread_count = %d; want 2", conv.UnreadCount)
	}

	// Messages stored.
	convMsgs, err := svc.GetMessages(ctx, conv.ConversationID)
	if err != nil {
		t.Fatalf("get messages: %v", err)
	}
	if len(convMsgs) != 2 {
		t.Fatalf("expected 2 messages, got %d", len(convMsgs))
	}
}

func TestMessengerIngest_Idempotent_NoDuplicateMessage(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildConvSvc(db)

	msgs, _ := messenger.ParseWebhookPayload([]byte(messengerFixture))

	// Ingest the same payload twice.
	for round := 0; round < 2; round++ {
		for _, msg := range msgs {
			if err := svc.IngestMessage(ctx, msg); err != nil {
				t.Fatalf("round %d ingest %s: %v", round, msg.ExternalMessageID, err)
			}
		}
	}

	convs, _ := svc.ListInbox(ctx, "", "")
	if len(convs) != 1 {
		t.Fatalf("expected 1 conversation after duplicate ingest, got %d", len(convs))
	}
	convMsgs, _ := svc.GetMessages(ctx, convs[0].ConversationID)
	if len(convMsgs) != 2 {
		t.Fatalf("expected 2 messages (no duplicates), got %d", len(convMsgs))
	}
}

func TestMessengerIngest_KnownPSID_LinksParty(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()

	// Register the psid=12345 as a known party identity.
	partyID := seedPartyWithPSID(t, db, "12345")

	svc := buildConvSvc(db)
	msgs, _ := messenger.ParseWebhookPayload([]byte(messengerFixture))
	for _, msg := range msgs {
		if err := svc.IngestMessage(ctx, msg); err != nil {
			t.Fatalf("ingest: %v", err)
		}
	}

	convs, _ := svc.ListInbox(ctx, "", "")
	if len(convs) != 1 {
		t.Fatalf("expected 1 conversation, got %d", len(convs))
	}
	if convs[0].PartyID == nil {
		t.Fatal("party_id should be linked for known psid")
	}
	if *convs[0].PartyID != partyID {
		t.Errorf("party_id = %q; want %q", *convs[0].PartyID, partyID)
	}
}

func TestMessengerIngest_UnknownPSID_PartyIDNull(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildConvSvc(db)

	// No party registered for psid=12345.
	msgs, _ := messenger.ParseWebhookPayload([]byte(messengerFixture))
	for _, msg := range msgs {
		if err := svc.IngestMessage(ctx, msg); err != nil {
			t.Fatalf("ingest: %v", err)
		}
	}

	convs, _ := svc.ListInbox(ctx, "", "")
	if len(convs) != 1 {
		t.Fatalf("expected 1 conversation, got %d", len(convs))
	}
	if convs[0].PartyID != nil {
		t.Errorf("party_id should be nil for unknown psid, got %q", *convs[0].PartyID)
	}
}

// ─── Inbox assign / close ─────────────────────────────────────────────────────

func TestInbox_AssignAndClose(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildConvSvc(db)

	// Create a conversation via ingest.
	msgs, _ := messenger.ParseWebhookPayload([]byte(messengerFixture))
	for _, msg := range msgs {
		_ = svc.IngestMessage(ctx, msg)
	}

	convs, _ := svc.ListInbox(ctx, "", "open")
	if len(convs) != 1 {
		t.Fatalf("expected 1 open conversation, got %d", len(convs))
	}
	convID := convs[0].ConversationID

	// Seed a user to assign.
	userID := uuid.New().String()
	_, err := db.SQLDB().ExecContext(ctx,
		`INSERT INTO crm_app_user (user_id, email, full_name, role) VALUES (?, ?, ?, ?)`,
		userID, "agent@crm.local", "Agent One", "sales",
	)
	if err != nil {
		t.Fatalf("seed user: %v", err)
	}

	// Assign.
	if err := svc.AssignConversation(ctx, convID, userID); err != nil {
		t.Fatalf("assign conversation: %v", err)
	}

	// Verify assignment.
	byAssignee, err := svc.ListInbox(ctx, userID, "")
	if err != nil {
		t.Fatalf("list by assignee: %v", err)
	}
	if len(byAssignee) != 1 {
		t.Fatalf("expected 1 conversation for assignee, got %d", len(byAssignee))
	}

	// Close the conversation.
	if err := svc.SetStatus(ctx, convID, "closed"); err != nil {
		t.Fatalf("close conversation: %v", err)
	}
	closed, _ := svc.ListInbox(ctx, "", "closed")
	if len(closed) != 1 {
		t.Fatalf("expected 1 closed conversation, got %d", len(closed))
	}

	// Re-open.
	if err := svc.SetStatus(ctx, convID, "open"); err != nil {
		t.Fatalf("re-open conversation: %v", err)
	}
	open, _ := svc.ListInbox(ctx, "", "open")
	if len(open) != 1 {
		t.Fatalf("expected 1 open conversation after re-open, got %d", len(open))
	}
}

// ─── Task assign ──────────────────────────────────────────────────────────────

func TestTask_AssignAndList(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildTaskSvc(db)

	userID := uuid.New().String()
	_, err := db.SQLDB().ExecContext(ctx,
		`INSERT INTO crm_app_user (user_id, email, full_name, role) VALUES (?, ?, ?, ?)`,
		userID, "rep@crm.local", "Sales Rep", "sales",
	)
	if err != nil {
		t.Fatalf("seed user: %v", err)
	}

	task := &domain.Task{Title: "Call VIP customer"}
	if err := svc.CreateTask(ctx, task); err != nil {
		t.Fatalf("create task: %v", err)
	}

	if err := svc.AssignTask(ctx, task.TaskID, userID); err != nil {
		t.Fatalf("assign task: %v", err)
	}

	tasks, err := svc.ListTasks(ctx, userID, "open")
	if err != nil {
		t.Fatalf("list tasks: %v", err)
	}
	if len(tasks) != 1 {
		t.Fatalf("expected 1 task for assignee, got %d", len(tasks))
	}
	if tasks[0].AssigneeUserID == nil || *tasks[0].AssigneeUserID != userID {
		t.Errorf("assignee_user_id = %v; want %s", tasks[0].AssigneeUserID, userID)
	}
}

// ─── Fix #1/#2: Echo thread key + atomic unread_count ────────────────────────

// echoFixture is a webhook payload with one inbound and one echo (page-sent) message
// on the same conversation thread (customer psid=12345, page=99999).
const echoFixture = `{
  "object": "page",
  "entry": [{
    "id": "99999",
    "messaging": [
      {
        "sender":    {"id": "12345"},
        "recipient": {"id": "99999"},
        "timestamp": 1718323200000,
        "message": {"mid": "inb.001", "text": "Cho hỏi còn hàng không?"}
      },
      {
        "sender":    {"id": "99999"},
        "recipient": {"id": "12345"},
        "timestamp": 1718323260000,
        "message": {"mid": "echo.001", "text": "Còn bạn nhé!", "is_echo": true}
      }
    ]
  }]
}`

// TestParser_EchoMessage_ThreadKeyIsRecipient integration-level check:
// both messages land in ONE conversation (same external_thread_id = "12345"),
// only the inbound message increments unread_count.
func TestParser_EchoMessage_ThreadKeyIsRecipient(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildConvSvc(db)

	msgs, err := messenger.ParseWebhookPayload([]byte(echoFixture))
	if err != nil {
		t.Fatalf("parse echo fixture: %v", err)
	}
	if len(msgs) != 2 {
		t.Fatalf("expected 2 parsed messages (1 in + 1 echo), got %d", len(msgs))
	}

	// Verify parser output before ingest.
	var inboundMsg, echoMsg *domain.ParsedMessage
	for i := range msgs {
		if msgs[i].Direction == "in" {
			inboundMsg = &msgs[i]
		} else {
			echoMsg = &msgs[i]
		}
	}
	if inboundMsg == nil {
		t.Fatal("no inbound message parsed")
	}
	if echoMsg == nil {
		t.Fatal("no echo message parsed")
	}
	// Echo thread key must be the customer psid (recipient.id), not the page id.
	if echoMsg.ExternalThreadID != "12345" {
		t.Errorf("echo ExternalThreadID = %q; want 12345 (customer psid)", echoMsg.ExternalThreadID)
	}
	if echoMsg.Direction != "out" {
		t.Errorf("echo Direction = %q; want out", echoMsg.Direction)
	}

	// Ingest both.
	for _, msg := range msgs {
		if err := svc.IngestMessage(ctx, msg); err != nil {
			t.Fatalf("ingest %s: %v", msg.ExternalMessageID, err)
		}
	}

	// Expect ONE conversation (both keyed on psid=12345).
	convs, err := svc.ListInbox(ctx, "", "")
	if err != nil {
		t.Fatalf("list inbox: %v", err)
	}
	if len(convs) != 1 {
		t.Fatalf("expected 1 conversation (echo and inbound share thread), got %d", len(convs))
	}
	conv := convs[0]
	if conv.ExternalThreadID != "12345" {
		t.Errorf("ExternalThreadID = %q; want 12345", conv.ExternalThreadID)
	}

	// Only the inbound message should have incremented unread_count.
	if conv.UnreadCount != 1 {
		t.Errorf("unread_count = %d; want 1 (echo must not increment unread)", conv.UnreadCount)
	}

	// Both messages stored in the same conversation.
	convMsgs, err := svc.GetMessages(ctx, conv.ConversationID)
	if err != nil {
		t.Fatalf("get messages: %v", err)
	}
	if len(convMsgs) != 2 {
		t.Fatalf("expected 2 messages in conversation, got %d", len(convMsgs))
	}
}

// TestMessengerIngest_Idempotent_UnreadCountNotDoubled verifies that ingesting
// the same payload twice keeps message count stable AND unread_count is not doubled.
func TestMessengerIngest_Idempotent_UnreadCountNotDoubled(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildConvSvc(db)

	msgs, _ := messenger.ParseWebhookPayload([]byte(messengerFixture))

	// First ingest.
	for _, msg := range msgs {
		if err := svc.IngestMessage(ctx, msg); err != nil {
			t.Fatalf("first ingest %s: %v", msg.ExternalMessageID, err)
		}
	}
	// Second ingest of identical payload.
	for _, msg := range msgs {
		if err := svc.IngestMessage(ctx, msg); err != nil {
			t.Fatalf("second ingest %s: %v", msg.ExternalMessageID, err)
		}
	}

	convs, err := svc.ListInbox(ctx, "", "")
	if err != nil {
		t.Fatalf("list inbox: %v", err)
	}
	if len(convs) != 1 {
		t.Fatalf("expected 1 conversation, got %d", len(convs))
	}
	conv := convs[0]

	// Message count must be stable (no duplicates).
	convMsgs, err := svc.GetMessages(ctx, conv.ConversationID)
	if err != nil {
		t.Fatalf("get messages: %v", err)
	}
	if len(convMsgs) != 2 {
		t.Fatalf("message count = %d after duplicate ingest; want 2", len(convMsgs))
	}

	// unread_count must NOT be doubled — atomic delta only applies on new insert.
	if conv.UnreadCount != 2 {
		t.Errorf("unread_count = %d; want 2 (not doubled by duplicate ingest)", conv.UnreadCount)
	}
}

// ─── Fix #3: DB-level task idempotency via unique index ──────────────────────

// TestGenerateTasksFromActionQueue_UniqueIndexPreventsDBDup verifies that even
// if the app-level ExistsBySourceRef check were bypassed, the DB unique index on
// (source, source_ref) prevents duplicate task rows.
func TestGenerateTasksFromActionQueue_UniqueIndexPreventsDBDup(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()

	// Seed one action.
	actions := []domain.ActionQueueItem{
		{ActionID: "IDX-001", CustomerKey: "CUST-X", ActionType: "WIN_BACK", RationaleVI: "Test dedup", Priority: 1},
	}
	seedActionQueueInCache(t, dataDir, actions)

	svc := buildTaskSvc(db)

	// First run: creates 1 task.
	n1, err := svc.GenerateTasksFromActionQueue(ctx)
	if err != nil {
		t.Fatalf("first run: %v", err)
	}
	if n1 != 1 {
		t.Fatalf("expected 1 task created, got %d", n1)
	}

	// Second run: app-level guard skips it (0 new tasks).
	n2, err := svc.GenerateTasksFromActionQueue(ctx)
	if err != nil {
		t.Fatalf("second run: %v", err)
	}
	if n2 != 0 {
		t.Errorf("expected 0 tasks on second run (idempotent), got %d", n2)
	}

	// Verify unique index exists in sqlite_master.
	var idxName string
	err = db.SQLDB().QueryRowContext(ctx,
		`SELECT name FROM sqlite_master WHERE type='index' AND name='uidx_task_source_ref'`,
	).Scan(&idxName)
	if err != nil {
		t.Fatalf("unique index uidx_task_source_ref not found: %v", err)
	}
	if idxName != "uidx_task_source_ref" {
		t.Errorf("index name = %q; want uidx_task_source_ref", idxName)
	}

	// Verify only 1 task row exists.
	var count int
	err = db.SQLDB().QueryRowContext(ctx,
		`SELECT COUNT(*) FROM crm_task WHERE source='action_queue' AND source_ref='IDX-001'`,
	).Scan(&count)
	if err != nil {
		t.Fatalf("count tasks: %v", err)
	}
	if count != 1 {
		t.Errorf("task count = %d; want 1 (DB-level dedup)", count)
	}
}

// ─── Fix #4: UpdateTask persists title + description ─────────────────────────

// TestUpdateTask_PersistsTitleAndDescription verifies that after an update call,
// title and description are not silently dropped.
func TestUpdateTask_PersistsTitleAndDescription(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildTaskSvc(db)

	task := &domain.Task{
		Title:       "Original title",
		Description: "Original description",
	}
	if err := svc.CreateTask(ctx, task); err != nil {
		t.Fatalf("create task: %v", err)
	}

	// Transition status triggers an Update call — title/description must survive.
	if err := svc.TransitionStatus(ctx, task.TaskID, "doing"); err != nil {
		t.Fatalf("transition status: %v", err)
	}

	got, err := svc.GetTask(ctx, task.TaskID)
	if err != nil {
		t.Fatalf("get task: %v", err)
	}
	if got.Title != "Original title" {
		t.Errorf("Title = %q after update; want 'Original title'", got.Title)
	}
	if got.Description != "Original description" {
		t.Errorf("Description = %q after update; want 'Original description'", got.Description)
	}
}

// ─── Fix: done→doing forbidden (explicit sub-test) ───────────────────────────

// TestTaskStatusTransitions_DoneToDoingForbidden verifies the specific transition
// done→doing is rejected by the domain rules.
func TestTaskStatusTransitions_DoneToDoingForbidden(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildTaskSvc(db)

	task := &domain.Task{Title: "Test task"}
	if err := svc.CreateTask(ctx, task); err != nil {
		t.Fatalf("create task: %v", err)
	}

	// Advance to done.
	if err := svc.TransitionStatus(ctx, task.TaskID, "done"); err != nil {
		t.Fatalf("open→done: %v", err)
	}

	// done→doing must be forbidden (not in allowed transitions).
	err := svc.TransitionStatus(ctx, task.TaskID, "doing")
	if err == nil {
		t.Fatal("expected error for done→doing transition, got nil")
	}
	if !domain.IsValidationError(err) {
		t.Errorf("expected ValidationError for forbidden transition, got: %T %v", err, err)
	}
}

// ─── Migration 0004 applied ──────────────────────────────────────────────────

func TestMigration0004_TablesExist(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	for _, tbl := range []string{"crm_activity", "crm_task", "crm_conversation", "crm_message"} {
		var n int
		err := db.SQLDB().QueryRowContext(ctx,
			fmt.Sprintf("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='%s'", tbl),
		).Scan(&n)
		if err != nil || n == 0 {
			t.Errorf("table %s not found after migration 0004", tbl)
		}
	}
}


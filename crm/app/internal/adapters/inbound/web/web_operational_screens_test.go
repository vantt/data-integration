// Package web_test — httptest-level tests for the operational UI screens:
// S04 Dedup Review, S05 Inbox, S06 Conversation Detail, S07 Tasks Board.
// Uses temp SQLite + embedded migrations; seeds the minimal data each test needs.
package web_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web"
	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite"
	"github.com/vantt/data-integration/crm/app/internal/application"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// ── extended fixture ──────────────────────────────────────────────────────────

// opFixture extends testFixture with the operational-screen services.
type opFixture struct {
	server  http.Handler
	partyID string
	convID  string
	taskID  string
	candID  string
}

func newOpFixture(t *testing.T) *opFixture {
	t.Helper()
	dir := t.TempDir()

	db, err := sqlite.Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })

	if err := sqlite.MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	now := time.Now().UTC().Format("2006-01-02T15:04:05.000Z")

	// Repos.
	partyRepo := sqlite.NewPartyRepo(db)
	dedupRepo := sqlite.NewDedupRepo(db)
	profileRepo := sqlite.NewProfileRepo(db)
	customFieldRepo := sqlite.NewCustomFieldRepo(db)
	tagRepo := sqlite.NewTagRepo(db)
	noteRepo := sqlite.NewNoteRepo(db)
	activityRepo := sqlite.NewActivityRepo(db)
	taskRepo := sqlite.NewTaskRepo(db)
	cacheRepo := sqlite.NewCacheRepo(db)
	convRepo := sqlite.NewConversationRepo(db)
	appUserRepo := sqlite.NewAppUserRepo(db)

	// Services.
	profileSvc := application.NewProfileService(profileRepo, customFieldRepo, tagRepo, noteRepo)
	activitySvc := application.NewActivityService(activityRepo)
	taskSvc := application.NewTaskService(taskRepo, partyRepo, cacheRepo)
	convSvc := application.NewConversationService(convRepo, partyRepo)
	mergeService := application.NewMergeService(partyRepo, dedupRepo)

	// Seed party A.
	partyA := &domain.Party{
		PartyID: "op-party-A", PartyType: "person",
		DisplayName: "Nguyễn Văn A", PrimaryPhone: "+84901111111",
		Status: "active", CreatedAt: now, UpdatedAt: now,
	}
	if err := partyRepo.Create(context.Background(), partyA); err != nil {
		t.Fatalf("seed partyA: %v", err)
	}

	// Seed party B (for dedup).
	partyB := &domain.Party{
		PartyID: "op-party-B", PartyType: "person",
		DisplayName: "Nguyen Van A", PrimaryPhone: "+84901111111",
		Status: "active", CreatedAt: now, UpdatedAt: now,
	}
	if err := partyRepo.Create(context.Background(), partyB); err != nil {
		t.Fatalf("seed partyB: %v", err)
	}

	// Seed dedup candidate.
	cand := &domain.DedupCandidate{
		CandidateID: "op-cand-001",
		PartyA:      partyA.PartyID,
		PartyB:      partyB.PartyID,
		MatchRule:   "exact_phone",
		MatchScore:  1.0,
		Status:      "pending",
		CreatedAt:   now,
	}
	if err := dedupRepo.InsertCandidate(context.Background(), cand); err != nil {
		t.Fatalf("seed dedup candidate: %v", err)
	}

	// Seed task.
	task := &domain.Task{
		TaskID: "op-task-001", Title: "Follow-up test",
		Status: "open", Source: "manual",
		CreatedAt: now, UpdatedAt: now,
	}
	if err := taskSvc.CreateTask(context.Background(), task); err != nil {
		t.Fatalf("seed task: %v", err)
	}

	// Seed conversation via IngestMessage.
	msg := domain.ParsedMessage{
		Channel:           "messenger",
		ExternalThreadID:  "psid-test-001",
		PageID:            "page-001",
		ExternalMessageID: "ext-msg-001",
		Direction:         "in",
		SenderRef:         "psid-test-001",
		Body:              "Tôi muốn hỏi đơn hàng",
		SentAt:            now,
	}
	if err := convSvc.IngestMessage(context.Background(), msg); err != nil {
		t.Fatalf("seed conversation: %v", err)
	}
	// Fetch the conversation ID that was created.
	convs, err := convSvc.ListInbox(context.Background(), "", "")
	if err != nil || len(convs) == 0 {
		t.Fatalf("list conversations after seed: %v (len=%d)", err, len(convs))
	}
	convID := convs[0].ConversationID

	// Wire web deps.
	deps := &web.Deps{
		ActionQueue:   cacheRepo,
		Tasks:         taskSvc,
		TaskWriter:    taskSvc,
		TaskCreator:   taskSvc,
		TaskGen:       taskSvc,
		Parties:       web.NewWebPartyRepo(partyRepo, db.SQLDB()),
		Profile:       profileSvc,
		Insight:       cacheRepo,
		Identities:    partyRepo,
		Activities:    activitySvc,
		Notes:         profileSvc,
		PartyTasks:    web.NewWebTaskRepo(db.SQLDB()),
		Conversations: convSvc,
		ConvWriter:    convSvc,
		ConvLinker:    web.NewWebConvRepo(convRepo, db.SQLDB()),
		AppUsers:      appUserRepo,
		Dedup:         dedupRepo,
		Merger:        mergeService,
		ActivityLog:   activitySvc,
	}

	r := chi.NewRouter()
	r.Use(middleware.Recoverer)
	web.Mount(r, deps)

	return &opFixture{
		server:  r,
		partyID: partyA.PartyID,
		convID:  convID,
		taskID:  task.TaskID,
		candID:  cand.CandidateID,
	}
}

// ── S05 Inbox tests ───────────────────────────────────────────────────────────

func TestInbox_GracefulEmpty(t *testing.T) {
	f := newOpFixture(t)
	// Request with a filter that matches nothing.
	req := httptest.NewRequest(http.MethodGet, "/inbox?status=closed", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /inbox?status=closed = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Hộp thư") {
		t.Error("inbox page missing 'Hộp thư'")
	}
}

func TestInbox_ShowsSeededConversation(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/inbox", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /inbox = %d; want 200", w.Code)
	}
	// Seeded conversation has no party link yet → "Chưa link khách" badge.
	body := w.Body.String()
	if !strings.Contains(body, "Chưa link khách") && !strings.Contains(body, "messenger") {
		t.Errorf("inbox missing expected conversation indicator; snippet: %.400s", body)
	}
}

// ── S06 Conversation Detail tests ─────────────────────────────────────────────

func TestConversationDetail_Renders(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/inbox/"+f.convID, nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /inbox/%s = %d; want 200; body: %.300s", f.convID, w.Code, w.Body.String())
	}
	body := w.Body.String()
	if !strings.Contains(body, "Tôi muốn hỏi đơn hàng") {
		t.Errorf("conv detail missing seeded message body; snippet: %.400s", body)
	}
}

func TestConversationDetail_NotFound(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/inbox/does-not-exist-99", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("GET /inbox/bad = %d; want 404", w.Code)
	}
}

func TestConversationDetail_AssignModalFragment(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/inbox/"+f.convID+"/modal/assign", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("modal assign = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Gán NV") {
		t.Errorf("modal assign missing 'Gán NV'; snippet: %.300s", w.Body.String())
	}
}

func TestConversationDetail_CloseModalFragment(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/inbox/"+f.convID+"/modal/close", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("modal close = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Đóng hội thoại") {
		t.Errorf("modal close missing 'Đóng hội thoại'; snippet: %.300s", w.Body.String())
	}
}

func TestConversationDetail_CloseAction(t *testing.T) {
	f := newOpFixture(t)
	form := url.Values{}
	req := httptest.NewRequest(http.MethodPost, "/inbox/"+f.convID+"/close",
		strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST close = %d; want 200; body: %s", w.Code, w.Body.String())
	}
	if w.Header().Get("HX-Redirect") == "" {
		t.Error("close action missing HX-Redirect header")
	}
}

func TestConversationDetail_LinkPartyModalFragment(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/inbox/"+f.convID+"/modal/link-party", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("modal link-party = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Gắn khách") {
		t.Errorf("modal link-party missing 'Gắn khách'; snippet: %.300s", w.Body.String())
	}
}

func TestConversationDetail_LinkPartyAction(t *testing.T) {
	f := newOpFixture(t)
	form := url.Values{"party_id": {f.partyID}}
	req := httptest.NewRequest(http.MethodPost, "/inbox/"+f.convID+"/link-party",
		strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST link-party = %d; want 200; body: %s", w.Code, w.Body.String())
	}
	// After linking, the conversation detail should now show the party name.
	req2 := httptest.NewRequest(http.MethodGet, "/inbox/"+f.convID, nil)
	w2 := httptest.NewRecorder()
	f.server.ServeHTTP(w2, req2)
	if w2.Code != http.StatusOK {
		t.Errorf("GET conv after link = %d; want 200", w2.Code)
	}
	if !strings.Contains(w2.Body.String(), "Nguyễn Văn A") {
		t.Errorf("conv detail after link missing party name; snippet: %.400s", w2.Body.String())
	}
}

// ── S07 Tasks Board tests ─────────────────────────────────────────────────────

func TestTasksBoard_Renders(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/tasks", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /tasks = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Follow-up test") {
		t.Errorf("tasks board missing seeded task title; snippet: %.400s", w.Body.String())
	}
}

func TestTasksBoard_GracefulEmpty(t *testing.T) {
	f := newOpFixture(t)
	// Filter that matches no tasks.
	req := httptest.NewRequest(http.MethodGet, "/tasks?status=cancelled", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /tasks?status=cancelled = %d; want 200", w.Code)
	}
}

func TestTasksBoard_CreateModalFragment(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/tasks/modal/create", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("modal create task = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Tạo task mới") {
		t.Errorf("modal create missing 'Tạo task mới'; snippet: %.300s", w.Body.String())
	}
}

func TestTasksBoard_CreateTaskAction(t *testing.T) {
	f := newOpFixture(t)
	form := url.Values{
		"title":       {"Task từ test"},
		"description": {"Mô tả test"},
	}
	req := httptest.NewRequest(http.MethodPost, "/tasks",
		strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST /tasks = %d; want 200; body: %s", w.Code, w.Body.String())
	}
	// Verify the new task appears on the board.
	req2 := httptest.NewRequest(http.MethodGet, "/tasks", nil)
	w2 := httptest.NewRecorder()
	f.server.ServeHTTP(w2, req2)
	if !strings.Contains(w2.Body.String(), "Task từ test") {
		t.Errorf("tasks board missing newly created task; snippet: %.400s", w2.Body.String())
	}
}

func TestTasksBoard_StatusTransition(t *testing.T) {
	f := newOpFixture(t)
	form := url.Values{"status": {"done"}}
	req := httptest.NewRequest(http.MethodPatch, "/tasks/"+f.taskID+"/status",
		strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("PATCH task status = %d; want 200; body: %s", w.Code, w.Body.String())
	}
}

// ── S04 Dedup Review tests ────────────────────────────────────────────────────

func TestDedupReview_Renders(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/dedup", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /dedup = %d; want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "exact_phone") {
		t.Errorf("dedup page missing candidate match rule; snippet: %.400s", body)
	}
}

func TestDedupReview_GracefulEmpty(t *testing.T) {
	f := newOpFixture(t)
	// Filter to a rule with no candidates.
	req := httptest.NewRequest(http.MethodGet, "/dedup?match_rule=fts_name_phone", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /dedup (empty filter) = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Dedup Review") {
		t.Errorf("dedup page missing title on empty; snippet: %.300s", w.Body.String())
	}
}

func TestDedupReview_MergeModalFragment(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/dedup/"+f.candID+"/modal/merge", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("modal merge = %d; want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "Xác nhận gộp") {
		t.Errorf("modal merge missing 'Xác nhận gộp'; snippet: %.400s", body)
	}
}

func TestDedupReview_MergeAction(t *testing.T) {
	f := newOpFixture(t)
	form := url.Values{"confirm": {"1"}}
	req := httptest.NewRequest(http.MethodPost, "/dedup/"+f.candID+"/merge",
		strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST merge = %d; want 200; body: %s", w.Code, w.Body.String())
	}
	// After merge, the candidate should no longer appear as pending.
	req2 := httptest.NewRequest(http.MethodGet, "/dedup", nil)
	w2 := httptest.NewRecorder()
	f.server.ServeHTTP(w2, req2)
	// The candidate row should be gone (merged → not pending).
	if strings.Contains(w2.Body.String(), f.candID) {
		t.Errorf("dedup page still shows merged candidate; snippet: %.400s", w2.Body.String())
	}
}

func TestDedupReview_RejectAction(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodPost, "/dedup/"+f.candID+"/reject", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST reject = %d; want 200; body: %s", w.Code, w.Body.String())
	}
	// Candidate should now be absent from the pending list.
	req2 := httptest.NewRequest(http.MethodGet, "/dedup", nil)
	w2 := httptest.NewRecorder()
	f.server.ServeHTTP(w2, req2)
	if strings.Contains(w2.Body.String(), f.candID) {
		t.Errorf("dedup page still shows rejected candidate; snippet: %.400s", w2.Body.String())
	}
}

// ── #3 Customer 360 log-activity route ───────────────────────────────────────

// TestLogActivity_ModalRenders verifies GET /customers/{id}/modal/log-activity returns 200.
func TestLogActivity_ModalRenders(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/customers/"+f.partyID+"/modal/log-activity", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET modal/log-activity = %d; want 200; body: %.300s", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Ghi log") {
		t.Errorf("log-activity modal missing 'Ghi log'; snippet: %.300s", w.Body.String())
	}
}

// TestLogActivity_PostCreatesActivity verifies POST /customers/{id}/log-activity
// creates the activity and returns the refreshed timeline panel.
func TestLogActivity_PostCreatesActivity(t *testing.T) {
	f := newOpFixture(t)
	form := url.Values{
		"activity_type": {"call"},
		"body":          {"Gọi điện xác nhận đơn hàng"},
	}
	req := httptest.NewRequest(http.MethodPost, "/customers/"+f.partyID+"/log-activity",
		strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST log-activity = %d; want 200; body: %.300s", w.Code, w.Body.String())
	}
	// The response is the timeline panel fragment; it should contain the new activity body.
	if !strings.Contains(w.Body.String(), "Gọi điện xác nhận đơn hàng") {
		t.Errorf("timeline panel missing new activity; snippet: %.400s", w.Body.String())
	}
}

// TestLogActivity_MissingBody_Returns400 verifies that missing body returns 400.
func TestLogActivity_MissingBody_Returns400(t *testing.T) {
	f := newOpFixture(t)
	form := url.Values{"activity_type": {"call"}} // missing body
	req := httptest.NewRequest(http.MethodPost, "/customers/"+f.partyID+"/log-activity",
		strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Errorf("POST log-activity (missing body) = %d; want 400", w.Code)
	}
}

// ── #6 Link-party modal posts to correct conv URL ─────────────────────────────

// TestPartySearch_ResultsContainCorrectConvURL verifies the party search fragment
// embeds the correct /inbox/{convID}/link-party URL in each result's hx-post.
func TestPartySearch_ResultsContainCorrectConvURL(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodGet,
		"/inbox/"+f.convID+"/parties/search?q=Nguyễn", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("party search = %d; want 200; body: %.300s", w.Code, w.Body.String())
	}
	body := w.Body.String()
	expectedURL := "/inbox/" + f.convID + "/link-party"
	if !strings.Contains(body, expectedURL) {
		t.Errorf("party search results missing correct link-party URL %q; snippet: %.400s", expectedURL, body)
	}
}

// ── #7 Generate tasks from queue graceful-empty ───────────────────────────────

// TestGenerateTasksFromQueue_GracefulEmpty verifies POST /tasks/generate
// returns 200 (with HX-Redirect) even when the action queue is empty.
func TestGenerateTasksFromQueue_GracefulEmpty(t *testing.T) {
	f := newOpFixture(t)
	req := httptest.NewRequest(http.MethodPost, "/tasks/generate", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST /tasks/generate = %d; want 200; body: %.300s", w.Code, w.Body.String())
	}
	if w.Header().Get("HX-Redirect") != "/tasks" {
		t.Errorf("POST /tasks/generate missing HX-Redirect to /tasks; got %q", w.Header().Get("HX-Redirect"))
	}
}

// Package web_test — httptest-level tests for management UI screens:
// S08 Segments, S09 Segment builder, S10 Campaigns, S11 Campaign detail, S13 Settings.
// Uses temp SQLite + embedded migrations; seeds minimal data per test.
package web_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web"
	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite"
	"github.com/vantt/data-integration/crm/app/internal/application"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ── management fixture ────────────────────────────────────────────────────────

// mgmtFixture holds a wired web server for management screen tests.
type mgmtFixture struct {
	server     http.Handler
	partyID    string
	segmentID  string
	campaignID string
}

// newMgmtFixture opens a temp DB, migrates, seeds one party + segment + campaign,
// and returns a wired chi server covering all management routes.
func newMgmtFixture(t *testing.T) *mgmtFixture {
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
	segmentRepo := sqlite.NewSegmentRepo(db)
	campaignRepo := sqlite.NewCampaignRepo(db)

	// Services.
	profileSvc := application.NewProfileService(profileRepo, customFieldRepo, tagRepo, noteRepo)
	activitySvc := application.NewActivityService(activityRepo)
	taskSvc := application.NewTaskService(taskRepo, partyRepo, cacheRepo)
	convSvc := application.NewConversationService(convRepo, partyRepo)
	mergeService := application.NewMergeService(partyRepo, dedupRepo)
	segmentSvc := application.NewSegmentService(segmentRepo, db.SQLDB())
	campaignSvc := application.NewCampaignService(campaignRepo, segmentRepo, partyRepo, db.SQLDB())

	// Seed party.
	party := &domain.Party{
		PartyID: "mgmt-party-001", PartyType: "person",
		DisplayName: "Nguyễn Văn Quản Lý", PrimaryPhone: "+84901000001",
		Status: "active", CreatedAt: now, UpdatedAt: now,
	}
	if err := partyRepo.Create(context.Background(), party); err != nil {
		t.Fatalf("seed party: %v", err)
	}

	// Seed segment.
	seg := &domain.Segment{
		SegmentID:   "mgmt-seg-001",
		Name:        "VIP customers",
		Description: "Top buyers",
		IsDynamic:   false,
		CreatedAt:   now,
		UpdatedAt:   now,
	}
	if err := segmentSvc.CreateSegment(context.Background(), seg); err != nil {
		t.Fatalf("seed segment: %v", err)
	}

	// Seed campaign.
	segID := seg.SegmentID
	camp := &domain.Campaign{
		CampaignID: "mgmt-camp-001",
		Name:       "Tái kích hoạt tháng 6",
		Objective:  "reactivation",
		SegmentID:  &segID,
		Status:     "draft",
		CreatedAt:  now,
		UpdatedAt:  now,
	}
	if err := campaignSvc.CreateCampaign(context.Background(), camp); err != nil {
		t.Fatalf("seed campaign: %v", err)
	}

	// Wire deps.
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
		PartyCreator:  partyRepo,
		OwnerAssigner: profileSvc,
		Segments:      segmentSvc,
		Campaigns:     campaignSvc,
		SettingsMgr:   profileSvc,
	}

	r := chi.NewRouter()
	r.Use(middleware.Recoverer)
	web.Mount(r, deps)

	return &mgmtFixture{
		server:     r,
		partyID:    party.PartyID,
		segmentID:  seg.SegmentID,
		campaignID: camp.CampaignID,
	}
}

// ── helper ────────────────────────────────────────────────────────────────────

func doGET(f *mgmtFixture, path string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodGet, path, nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	return w
}

func doPOST(f *mgmtFixture, path string, vals url.Values) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodPost, path, strings.NewReader(vals.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	return w
}

// ── S08 Segments list ─────────────────────────────────────────────────────────

func TestSegmentsList_GracefulEmpty(t *testing.T) {
	// Use a fresh fixture with no segments seeded (fresh DB, wired manually).
	dir := t.TempDir()
	db, err := sqlite.Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	if err := sqlite.MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

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
	segmentRepo := sqlite.NewSegmentRepo(db)
	campaignRepo := sqlite.NewCampaignRepo(db)

	profileSvc := application.NewProfileService(profileRepo, customFieldRepo, tagRepo, noteRepo)
	activitySvc := application.NewActivityService(activityRepo)
	taskSvc := application.NewTaskService(taskRepo, partyRepo, cacheRepo)
	convSvc := application.NewConversationService(convRepo, partyRepo)
	mergeService := application.NewMergeService(partyRepo, dedupRepo)
	segmentSvc := application.NewSegmentService(segmentRepo, db.SQLDB())
	campaignSvc := application.NewCampaignService(campaignRepo, segmentRepo, partyRepo, db.SQLDB())

	deps := &web.Deps{
		ActionQueue: cacheRepo, Tasks: taskSvc, TaskWriter: taskSvc, TaskCreator: taskSvc, TaskGen: taskSvc,
		Parties: web.NewWebPartyRepo(partyRepo, db.SQLDB()), Profile: profileSvc,
		Insight: cacheRepo, Identities: partyRepo, Activities: activitySvc, Notes: profileSvc,
		PartyTasks: web.NewWebTaskRepo(db.SQLDB()), Conversations: convSvc, ConvWriter: convSvc,
		ConvLinker: web.NewWebConvRepo(convRepo, db.SQLDB()), AppUsers: appUserRepo,
		Dedup: dedupRepo, Merger: mergeService, ActivityLog: activitySvc,
		PartyCreator: partyRepo, OwnerAssigner: profileSvc,
		Segments: segmentSvc, Campaigns: campaignSvc, SettingsMgr: profileSvc,
	}
	r := chi.NewRouter()
	r.Use(middleware.Recoverer)
	web.Mount(r, deps)

	req := httptest.NewRequest(http.MethodGet, "/segments", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("GET /segments = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Segments") {
		t.Errorf("segments page missing 'Segments'; snippet: %.400s", w.Body.String())
	}
}

func TestSegmentsList_ShowsSeededSegment(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/segments")
	if w.Code != http.StatusOK {
		t.Errorf("GET /segments = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "VIP customers") {
		t.Errorf("segments list missing seeded segment name; snippet: %.400s", w.Body.String())
	}
}

func TestSegmentBuilder_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/segments/new")
	if w.Code != http.StatusOK {
		t.Errorf("GET /segments/new = %d; want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "Tạo phân khúc") && !strings.Contains(body, "segment") {
		t.Errorf("segment builder page missing expected content; snippet: %.400s", body)
	}
}

func TestSegmentCreate_Works(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{
		"name":         {"Nhóm thử nghiệm"},
		"description":  {"Mô tả"},
		"segment_type": {"static"},
	}
	w := doPOST(f, "/segments", vals)
	// Expect HX-Redirect (200) or redirect (302/303).
	if w.Code != http.StatusOK && w.Code != http.StatusSeeOther {
		t.Errorf("POST /segments = %d; want 200 or 303; body: %.300s", w.Code, w.Body.String())
	}
}

func TestSegmentEdit_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/segments/"+f.segmentID)
	if w.Code != http.StatusOK {
		t.Errorf("GET /segments/%s = %d; want 200", f.segmentID, w.Code)
	}
	if !strings.Contains(w.Body.String(), "VIP customers") {
		t.Errorf("segment builder edit missing segment name; snippet: %.400s", w.Body.String())
	}
}

func TestSegmentRefresh_Works(t *testing.T) {
	f := newMgmtFixture(t)
	req := httptest.NewRequest(http.MethodPost, "/segments/"+f.segmentID+"/refresh", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST /segments/%s/refresh = %d; want 200; body: %.300s", f.segmentID, w.Code, w.Body.String())
	}
}

func TestSegmentAddMember_Works(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{"party_id": {f.partyID}}
	w := doPOST(f, "/segments/"+f.segmentID+"/members", vals)
	if w.Code != http.StatusOK && w.Code != http.StatusNoContent {
		t.Errorf("POST /segments/%s/members = %d; want 200/204; body: %.300s", f.segmentID, w.Code, w.Body.String())
	}
}

// ── S10 Campaigns list ────────────────────────────────────────────────────────

func TestCampaignsList_GracefulEmpty(t *testing.T) {
	f := newMgmtFixture(t)
	// Request campaigns list — seeded campaign should appear (not truly empty, but page renders).
	w := doGET(f, "/campaigns")
	if w.Code != http.StatusOK {
		t.Errorf("GET /campaigns = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Chiến dịch") {
		t.Errorf("campaigns page missing 'Chiến dịch'; snippet: %.400s", w.Body.String())
	}
}

func TestCampaignsList_ShowsSeededCampaign(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/campaigns")
	if w.Code != http.StatusOK {
		t.Errorf("GET /campaigns = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Tái kích hoạt tháng 6") {
		t.Errorf("campaigns list missing seeded campaign name; snippet: %.400s", w.Body.String())
	}
}

func TestCampaignCreate_Works(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{
		"name":       {"Chiến dịch mới"},
		"objective":  {"reactivation"},
		"segment_id": {f.segmentID},
	}
	w := doPOST(f, "/campaigns", vals)
	if w.Code != http.StatusOK && w.Code != http.StatusSeeOther {
		t.Errorf("POST /campaigns = %d; want 200/303; body: %.300s", w.Code, w.Body.String())
	}
}

func TestCampaignDetail_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/campaigns/"+f.campaignID)
	if w.Code != http.StatusOK {
		t.Errorf("GET /campaigns/%s = %d; want 200", f.campaignID, w.Code)
	}
	if !strings.Contains(w.Body.String(), "Tái kích hoạt tháng 6") {
		t.Errorf("campaign detail missing campaign name; snippet: %.400s", w.Body.String())
	}
}

func TestCampaignGenerateTargets_GracefulEmpty(t *testing.T) {
	f := newMgmtFixture(t)
	// Segment has no members, so generate targets returns 0 — still 200.
	req := httptest.NewRequest(http.MethodPost, "/campaigns/"+f.campaignID+"/generate-targets", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST /campaigns/%s/generate-targets = %d; want 200; body: %.300s", f.campaignID, w.Code, w.Body.String())
	}
}

func TestCampaignScanConversions_GracefulEmpty(t *testing.T) {
	f := newMgmtFixture(t)
	// No targets seeded, scan returns 0 conversions — still 200.
	req := httptest.NewRequest(http.MethodPost, "/campaigns/"+f.campaignID+"/scan-conversions", nil)
	w := httptest.NewRecorder()
	f.server.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("POST /campaigns/%s/scan-conversions = %d; want 200; body: %.300s", f.campaignID, w.Code, w.Body.String())
	}
}

func TestCampaignModalCreate_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/campaigns/modal/create")
	if w.Code != http.StatusOK {
		t.Errorf("GET /campaigns/modal/create = %d; want 200", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Tạo chiến dịch") {
		t.Errorf("campaign modal missing 'Tạo chiến dịch'; snippet: %.400s", w.Body.String())
	}
}

// ── S13 Settings ──────────────────────────────────────────────────────────────

func TestSettings_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/settings")
	if w.Code != http.StatusOK {
		t.Errorf("GET /settings = %d; want 200", w.Code)
	}
	body := w.Body.String()
	if !strings.Contains(body, "Cài đặt") && !strings.Contains(body, "settings") {
		t.Errorf("settings page missing expected heading; snippet: %.400s", body)
	}
}

func TestSettings_TagsTab_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/settings?tab=tags")
	if w.Code != http.StatusOK {
		t.Errorf("GET /settings?tab=tags = %d; want 200", w.Code)
	}
}

func TestSettings_UsersTab_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/settings?tab=users")
	if w.Code != http.StatusOK {
		t.Errorf("GET /settings?tab=users = %d; want 200", w.Code)
	}
}

func TestCustomFieldCreate_Works(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{
		"field_key": {"zalo_id"},
		"label":     {"Zalo ID"},
		"data_type": {"text"},
	}
	w := doPOST(f, "/settings/custom-fields", vals)
	if w.Code != http.StatusOK && w.Code != http.StatusSeeOther {
		t.Errorf("POST /settings/custom-fields = %d; want 200/303; body: %.300s", w.Code, w.Body.String())
	}
}

func TestCustomFieldCreate_InvalidDataType_Returns400(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{
		"field_key": {"bad_field"},
		"label":     {"Bad field"},
		"data_type": {"not_a_valid_type"},
	}
	w := doPOST(f, "/settings/custom-fields", vals)
	if w.Code != http.StatusBadRequest {
		t.Errorf("POST /settings/custom-fields (bad data_type) = %d; want 400", w.Code)
	}
}

func TestTagCreate_Works(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{
		"name":     {"vip"},
		"label":    {"VIP"},
		"category": {"loyalty"},
		"color":    {"#FFD700"},
	}
	w := doPOST(f, "/settings/tags", vals)
	if w.Code != http.StatusOK && w.Code != http.StatusSeeOther {
		t.Errorf("POST /settings/tags = %d; want 200/303; body: %.300s", w.Code, w.Body.String())
	}
}

func TestTagCreate_MissingName_Returns400(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{"category": {"loyalty"}} // missing required name
	w := doPOST(f, "/settings/tags", vals)
	if w.Code != http.StatusBadRequest {
		t.Errorf("POST /settings/tags (missing name) = %d; want 400", w.Code)
	}
}

func TestTagCreate_InvalidColor_Returns400(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{
		"name":  {"test-tag"},
		"color": {"red"}, // not a valid #RRGGBB hex color
	}
	w := doPOST(f, "/settings/tags", vals)
	if w.Code != http.StatusBadRequest {
		t.Errorf("POST /settings/tags (invalid color) = %d; want 400", w.Code)
	}
}

func TestModalCustomFieldCreate_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/settings/custom-fields/modal/create")
	if w.Code != http.StatusOK {
		t.Errorf("GET /settings/custom-fields/modal/create = %d; want 200", w.Code)
	}
}

func TestModalTagCreate_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/settings/tags/modal/create")
	if w.Code != http.StatusOK {
		t.Errorf("GET /settings/tags/modal/create = %d; want 200", w.Code)
	}
}

// ── M02 Create Party (shared modal) ──────────────────────────────────────────

func TestModalCreateParty_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/parties/modal/create")
	if w.Code != http.StatusOK {
		t.Errorf("GET /parties/modal/create = %d; want 200", w.Code)
	}
}

func TestCreateParty_Works(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{
		"display_name": {"Khách Hàng Mới"},
		"phone":        {"+84900000099"},
		"email":        {"new@example.com"},
	}
	w := doPOST(f, "/parties", vals)
	// Expect HX-Redirect (200 with header).
	if w.Code != http.StatusOK {
		t.Errorf("POST /parties = %d; want 200; body: %.300s", w.Code, w.Body.String())
	}
	if !strings.HasPrefix(w.Header().Get("HX-Redirect"), "/customers/") {
		t.Errorf("POST /parties missing HX-Redirect to /customers/...; got %q", w.Header().Get("HX-Redirect"))
	}
}

func TestCreateParty_MissingPhone_Returns400(t *testing.T) {
	f := newMgmtFixture(t)
	vals := url.Values{"display_name": {"No Phone"}}
	w := doPOST(f, "/parties", vals)
	if w.Code != http.StatusBadRequest {
		t.Errorf("POST /parties (missing phone) = %d; want 400", w.Code)
	}
}

// ── M04 Assign Owner (shared modal) ──────────────────────────────────────────

func TestModalAssignOwner_Renders(t *testing.T) {
	f := newMgmtFixture(t)
	w := doGET(f, "/customers/"+f.partyID+"/modal/assign-owner")
	if w.Code != http.StatusOK {
		t.Errorf("GET /customers/%s/modal/assign-owner = %d; want 200", f.partyID, w.Code)
	}
}

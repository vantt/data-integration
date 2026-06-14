// Package sqlite — Phase 06 integration tests: segments + campaigns.
// Uses a real temp SQLite DB with migrations 0001-0005 applied; no mocks.
// Cache tables (wh_customer_insight, wh_order_hdr) are seeded directly into
// the writable cache.db file (same pattern as Phase 05 action-queue tests).
package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"path/filepath"
	"testing"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/application"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── helpers ─────────────────────────────────────────────────────────────────

func buildSegmentSvc(db *DB) *application.SegmentService {
	return application.NewSegmentService(NewSegmentRepo(db), db.SQLDB())
}

func buildCampaignSvc(db *DB) *application.CampaignService {
	return application.NewCampaignService(
		NewCampaignRepo(db),
		NewSegmentRepo(db),
		NewPartyRepo(db),
		db.SQLDB(),
	)
}

// seedInsightInCache creates wh_customer_insight rows in cache.db directly.
func seedInsightInCache(t *testing.T, dataDir string, rows []struct {
	customerID     int64
	valueGroup     string
	customerStatus string
	channelPref    string
}) {
	t.Helper()
	ctx := context.Background()
	cacheDSN := "file:" + filepath.ToSlash(filepath.Join(dataDir, "cache.db"))
	conn, err := sql.Open("sqlite", cacheDSN)
	if err != nil {
		t.Fatalf("open cache.db: %v", err)
	}
	defer conn.Close()

	_, err = conn.ExecContext(ctx, `
		CREATE TABLE IF NOT EXISTS wh_customer_insight (
			customer_key    TEXT,
			customer_id     INTEGER PRIMARY KEY,
			value_group     TEXT,
			customer_status TEXT,
			next_purchase_signal TEXT,
			predicted_next_purchase_date TEXT,
			avg_days_between_orders REAL,
			avg_order_spend REAL,
			discount_sensitivity TEXT,
			cancel_rate REAL,
			last_purchased_sku TEXT,
			top_affinity_product TEXT,
			second_affinity_product TEXT,
			channel_preference TEXT,
			lifetime_contribution_margin REAL,
			is_margin_negative INTEGER DEFAULT 0,
			refreshed_at TEXT
		)`)
	if err != nil {
		t.Fatalf("create wh_customer_insight: %v", err)
	}

	for _, row := range rows {
		_, err := conn.ExecContext(ctx,
			`INSERT OR REPLACE INTO wh_customer_insight
				(customer_id, customer_key, value_group, customer_status, channel_preference, refreshed_at)
			 VALUES (?, ?, ?, ?, ?, '2026-01-01T00:00:00.000Z')`,
			row.customerID, fmt.Sprintf("CUST-%d", row.customerID),
			row.valueGroup, row.customerStatus, row.channelPref,
		)
		if err != nil {
			t.Fatalf("insert insight %d: %v", row.customerID, err)
		}
	}
}

// seedOrdersInCache seeds wh_order_hdr into cache.db.
func seedOrdersInCache(t *testing.T, dataDir string, orders []struct {
	orderCode  string
	customerID int64
	dateKey    int
	netRevenue int64
}) {
	t.Helper()
	ctx := context.Background()
	cacheDSN := "file:" + filepath.ToSlash(filepath.Join(dataDir, "cache.db"))
	conn, err := sql.Open("sqlite", cacheDSN)
	if err != nil {
		t.Fatalf("open cache.db: %v", err)
	}
	defer conn.Close()

	_, err = conn.ExecContext(ctx, `
		CREATE TABLE IF NOT EXISTS wh_order_hdr (
			order_id    TEXT PRIMARY KEY,
			order_code  TEXT,
			customer_id INTEGER,
			date_key    INTEGER,
			net_revenue INTEGER,
			status      TEXT,
			channel     TEXT,
			item_count  INTEGER
		)`)
	if err != nil {
		t.Fatalf("create wh_order_hdr: %v", err)
	}

	for _, o := range orders {
		_, err := conn.ExecContext(ctx,
			`INSERT OR REPLACE INTO wh_order_hdr
				(order_id, order_code, customer_id, date_key, net_revenue, status, channel, item_count)
			 VALUES (?, ?, ?, ?, ?, 'complete', 'online', 1)`,
			uuid.New().String(), o.orderCode, o.customerID, o.dateKey, o.netRevenue,
		)
		if err != nil {
			t.Fatalf("insert order %s: %v", o.orderCode, err)
		}
	}
}

// seedPartyWithSapoIdentity creates a party and a sapo_customer identity returning (partyID, customerID).
func seedPartyWithSapoIdentity(t *testing.T, db *DB, name string, customerID int64) string {
	t.Helper()
	ctx := context.Background()
	party := makeParty(name, "", "")
	partyRepo := NewPartyRepo(db)
	if err := partyRepo.Create(ctx, party); err != nil {
		t.Fatalf("seed party %s: %v", name, err)
	}
	id := &domain.PartyIdentity{
		IdentityID:    uuid.New().String(),
		PartyID:       party.PartyID,
		SourceSystem:  "sapo",
		IdentityType:  "sapo_customer",
		IdentityValue: fmt.Sprintf("%d", customerID),
		Confidence:    1.0,
		CreatedAt:     utcTestNow(),
	}
	if err := partyRepo.UpsertIdentity(ctx, id); err != nil {
		t.Fatalf("seed identity: %v", err)
	}
	return party.PartyID
}

// seedUserID inserts an app_user row and returns the user_id.
func seedUserID(t *testing.T, db *DB) string {
	t.Helper()
	userID := uuid.New().String()
	_, err := db.SQLDB().ExecContext(context.Background(),
		`INSERT INTO crm_app_user (user_id, email, full_name, role) VALUES (?, ?, ?, ?)`,
		userID, uuid.New().String()+"@crm.local", "Test User", "sales",
	)
	if err != nil {
		t.Fatalf("seed user: %v", err)
	}
	return userID
}

// ─── Migration 0005 applied ──────────────────────────────────────────────────

func TestMigration0005_TablesExist(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	for _, tbl := range []string{"crm_segment", "crm_segment_member", "crm_campaign", "crm_campaign_target"} {
		var n int
		err := db.SQLDB().QueryRowContext(ctx,
			"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", tbl,
		).Scan(&n)
		if err != nil || n == 0 {
			t.Errorf("table %s not found after migration 0005", tbl)
		}
	}
}

// ─── Segment CRUD ────────────────────────────────────────────────────────────

func TestSegment_CreateAndGet(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	seg := &domain.Segment{
		Name:        "VIP At-Risk",
		Description: "VIP customers who haven't bought in 60 days",
		IsDynamic:   true,
		Definition:  `{"value_group":["VIP"],"customer_status":"at_risk"}`,
	}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	if seg.SegmentID == "" {
		t.Fatal("segment_id should be set after create")
	}

	got, err := svc.GetSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("get segment: %v", err)
	}
	if got == nil {
		t.Fatal("segment not found after create")
	}
	if got.Name != "VIP At-Risk" {
		t.Errorf("name = %q; want VIP At-Risk", got.Name)
	}
	if !got.IsDynamic {
		t.Error("is_dynamic should be true")
	}
}

func TestSegment_EmptyName_Rejected(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	svc := buildSegmentSvc(db)
	err := svc.CreateSegment(context.Background(), &domain.Segment{Name: " "})
	if err == nil || !domain.IsValidationError(err) {
		t.Fatalf("expected ValidationError for empty name, got: %v", err)
	}
}

// ─── Segment rule evaluator ──────────────────────────────────────────────────

func TestSegmentRefresh_MatchingParties(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	// Seed 3 parties with sapo customer identities.
	// customerID 101 → VIP + at_risk  → should match
	// customerID 102 → GOLD + at_risk → should NOT match (not in value_group)
	// customerID 103 → VIP + active   → should NOT match (wrong status)
	partyVIPAtRisk := seedPartyWithSapoIdentity(t, db, "VIP At-Risk Customer", 101)
	_ = seedPartyWithSapoIdentity(t, db, "GOLD At-Risk Customer", 102)
	_ = seedPartyWithSapoIdentity(t, db, "VIP Active Customer", 103)

	seedInsightInCache(t, dataDir, []struct {
		customerID     int64
		valueGroup     string
		customerStatus string
		channelPref    string
	}{
		{101, "VIP", "at_risk", ""},
		{102, "GOLD", "at_risk", ""},
		{103, "VIP", "active", ""},
	})

	// Create a dynamic segment matching VIP + at_risk.
	seg := &domain.Segment{
		Name:       "VIP At-Risk",
		IsDynamic:  true,
		Definition: `{"value_group":["VIP"],"customer_status":"at_risk"}`,
	}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}

	n, err := svc.RefreshDynamicSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("refresh segment: %v", err)
	}
	if n != 1 {
		t.Errorf("expected 1 member (VIP+at_risk), got %d", n)
	}

	members, err := svc.ListMembers(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("list members: %v", err)
	}
	if len(members) != 1 {
		t.Fatalf("expected 1 member, got %d", len(members))
	}
	if members[0].PartyID != partyVIPAtRisk {
		t.Errorf("member party_id = %q; want %q (VIP at-risk)", members[0].PartyID, partyVIPAtRisk)
	}
	if members[0].Source != "rule" {
		t.Errorf("source = %q; want rule", members[0].Source)
	}
}

func TestSegmentRefresh_Idempotent(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	seedPartyWithSapoIdentity(t, db, "VIP Customer", 201)
	seedInsightInCache(t, dataDir, []struct {
		customerID     int64
		valueGroup     string
		customerStatus string
		channelPref    string
	}{
		{201, "VIP", "at_risk", ""},
	})

	seg := &domain.Segment{
		Name:       "Test Idempotent",
		IsDynamic:  true,
		Definition: `{"value_group":["VIP"]}`,
	}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}

	// Refresh twice — member count must stay at 1.
	n1, err := svc.RefreshDynamicSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("first refresh: %v", err)
	}
	n2, err := svc.RefreshDynamicSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("second refresh: %v", err)
	}
	if n1 != 1 || n2 != 1 {
		t.Errorf("expected 1 member each refresh; got %d, %d", n1, n2)
	}

	members, _ := svc.ListMembers(ctx, seg.SegmentID)
	if len(members) != 1 {
		t.Errorf("member count after 2 refreshes = %d; want 1 (idempotent)", len(members))
	}
}

func TestSegmentRefresh_UnknownKey_Rejected(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	seg := &domain.Segment{
		Name:       "Bad Rule",
		IsDynamic:  true,
		Definition: `{"value_group":["VIP"],"injected_key":"evil"}`, // injected_key not whitelisted
	}
	err := svc.CreateSegment(ctx, seg)
	if err == nil || !domain.IsValidationError(err) {
		t.Fatalf("expected ValidationError for unknown rule key, got: %v", err)
	}
}

func TestSegmentRefresh_CacheEmpty_ZeroMembersNoError(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	seg := &domain.Segment{
		Name:       "VIP Segment",
		IsDynamic:  true,
		Definition: `{"value_group":["VIP"]}`,
	}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}

	// No cache.wh_customer_insight → should return 0 members, no error.
	n, err := svc.RefreshDynamicSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("expected no error when cache empty, got: %v", err)
	}
	if n != 0 {
		t.Errorf("expected 0 members when cache empty, got %d", n)
	}
}

func TestSegmentRefresh_InjectionSafe(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	// A malicious value in a valid key — the value is parameterized, not interpolated.
	// If the query were built by string-interpolation, "' OR '1'='1" would break out.
	// With parameterized queries it is treated as a literal string value → 0 matches (not an error).
	seg := &domain.Segment{
		Name:       "Injection Test",
		IsDynamic:  true,
		Definition: `{"customer_status":"' OR '1'='1"}`,
	}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}

	// Must not error — the malicious value is parameterized and simply won't match any row.
	n, err := svc.RefreshDynamicSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("injection value caused an error (SQL injection may have occurred): %v", err)
	}
	if n != 0 {
		t.Errorf("injection value matched %d rows; expected 0 (no real rows with that status)", n)
	}
}

// ─── Manual segment member add/remove ────────────────────────────────────────

func TestSegmentMember_ManualAddRemove(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)
	party := makeParty("Manual Member", "", "")
	if err := NewPartyRepo(db).Create(ctx, party); err != nil {
		t.Fatalf("seed party: %v", err)
	}

	seg := &domain.Segment{Name: "Static Segment", IsDynamic: false}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}

	if err := svc.AddMember(ctx, seg.SegmentID, party.PartyID); err != nil {
		t.Fatalf("add member: %v", err)
	}
	members, _ := svc.ListMembers(ctx, seg.SegmentID)
	if len(members) != 1 {
		t.Fatalf("expected 1 member, got %d", len(members))
	}
	if members[0].Source != "manual" {
		t.Errorf("source = %q; want manual", members[0].Source)
	}

	if err := svc.RemoveMember(ctx, seg.SegmentID, party.PartyID); err != nil {
		t.Fatalf("remove member: %v", err)
	}
	members, _ = svc.ListMembers(ctx, seg.SegmentID)
	if len(members) != 0 {
		t.Errorf("expected 0 members after remove, got %d", len(members))
	}
}

// ─── Campaign CRUD ───────────────────────────────────────────────────────────

func TestCampaign_CreateAndList(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildCampaignSvc(db)

	c := &domain.Campaign{
		Name:      "Win-Back Q3",
		Objective: "winback",
		Channel:   "messenger",
	}
	if err := svc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if c.CampaignID == "" {
		t.Fatal("campaign_id should be set after create")
	}
	if c.Status != "draft" {
		t.Errorf("default status = %q; want draft", c.Status)
	}

	campaigns, err := svc.ListCampaigns(ctx)
	if err != nil {
		t.Fatalf("list campaigns: %v", err)
	}
	if len(campaigns) != 1 {
		t.Fatalf("expected 1 campaign, got %d", len(campaigns))
	}
}

func TestCampaign_InvalidObjective_Rejected(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	err := buildCampaignSvc(db).CreateCampaign(context.Background(), &domain.Campaign{
		Name:      "Bad",
		Objective: "spam", // not in valid set
	})
	if err == nil || !domain.IsValidationError(err) {
		t.Fatalf("expected ValidationError for invalid objective, got: %v", err)
	}
}

func TestCampaign_StatusTransitions(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildCampaignSvc(db)

	c := &domain.Campaign{Name: "Transition Test", Objective: "reactivation"}
	if err := svc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}

	// draft → running is valid.
	if err := svc.UpdateCampaign(ctx, c.CampaignID, &domain.Campaign{Status: "running"}); err != nil {
		t.Fatalf("draft→running: %v", err)
	}

	// running → done is valid.
	if err := svc.UpdateCampaign(ctx, c.CampaignID, &domain.Campaign{Status: "done"}); err != nil {
		t.Fatalf("running→done: %v", err)
	}

	// done → running is INVALID.
	err := svc.UpdateCampaign(ctx, c.CampaignID, &domain.Campaign{Status: "running"})
	if err == nil || !domain.IsValidationError(err) {
		t.Fatalf("expected ValidationError for done→running, got: %v", err)
	}
}

// ─── GenerateTargets ─────────────────────────────────────────────────────────

func TestCampaign_GenerateTargets_ExcludesNoConsent(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)
	partyRepo := NewPartyRepo(db)
	profileRepo := NewProfileRepo(db)

	// Party A: consent_contact = 1 (should be targeted).
	partyA := makeParty("Consenting Customer", "", "")
	if err := partyRepo.Create(ctx, partyA); err != nil {
		t.Fatalf("seed partyA: %v", err)
	}
	// Party B: consent_contact = 0 (must be excluded).
	partyB := makeParty("Non-Consenting Customer", "", "")
	if err := partyRepo.Create(ctx, partyB); err != nil {
		t.Fatalf("seed partyB: %v", err)
	}

	// Set consent_contact=0 for partyB via profile upsert.
	profileSvc := application.NewProfileService(profileRepo,
		NewCustomFieldRepo(db), NewTagRepo(db), NewNoteRepo(db))
	if err := profileSvc.UpsertProfile(ctx, &domain.CustomerProfile{
		PartyID:        partyB.PartyID,
		ConsentContact: false,
	}); err != nil {
		t.Fatalf("upsert partyB profile: %v", err)
	}

	// Create segment and add both parties manually.
	seg := &domain.Segment{Name: "All Parties", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyA.PartyID)
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyB.PartyID)

	// Create campaign linked to segment.
	c := &domain.Campaign{
		Name:      "Compliance Test Campaign",
		Objective: "reactivation",
		SegmentID: &seg.SegmentID,
	}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}

	n, err := campSvc.GenerateTargets(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("generate targets: %v", err)
	}
	// Only partyA should be targeted.
	if n != 1 {
		t.Errorf("expected 1 target (consent_contact=0 excluded), got %d", n)
	}

	targets, _ := campSvc.ListTargets(ctx, c.CampaignID, "")
	if len(targets) != 1 {
		t.Fatalf("expected 1 target row, got %d", len(targets))
	}
	if targets[0].PartyID != partyA.PartyID {
		t.Errorf("targeted party = %q; want %q (partyA)", targets[0].PartyID, partyA.PartyID)
	}
}

func TestCampaign_GenerateTargets_Idempotent(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)
	partyRepo := NewPartyRepo(db)

	party := makeParty("Customer", "", "")
	if err := partyRepo.Create(ctx, party); err != nil {
		t.Fatalf("seed party: %v", err)
	}

	seg := &domain.Segment{Name: "Seg", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, party.PartyID)

	c := &domain.Campaign{Name: "Campaign", Objective: "upsell", SegmentID: &seg.SegmentID}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}

	n1, err := campSvc.GenerateTargets(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("first generate: %v", err)
	}
	n2, err := campSvc.GenerateTargets(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("second generate: %v", err)
	}

	// Both runs succeed; second run adds 0 new targets (ON CONFLICT DO NOTHING).
	_ = n1
	targets, _ := campSvc.ListTargets(ctx, c.CampaignID, "")
	if len(targets) != 1 {
		t.Errorf("expected exactly 1 target after 2 generate calls, got %d", len(targets))
	}
	_ = n2
}

// ─── Target status transitions ────────────────────────────────────────────────

func TestCampaign_TargetStatusTransitions(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)
	partyRepo := NewPartyRepo(db)

	party := makeParty("Target Party", "", "")
	if err := partyRepo.Create(ctx, party); err != nil {
		t.Fatalf("seed party: %v", err)
	}
	seg := &domain.Segment{Name: "S", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, party.PartyID)

	c := &domain.Campaign{Name: "C", Objective: "winback", SegmentID: &seg.SegmentID}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if _, err := campSvc.GenerateTargets(ctx, c.CampaignID); err != nil {
		t.Fatalf("generate targets: %v", err)
	}

	// queued → sent is valid.
	if err := campSvc.UpdateTargetStatus(ctx, c.CampaignID, party.PartyID, "sent"); err != nil {
		t.Fatalf("queued→sent: %v", err)
	}
	// sent → responded is valid.
	if err := campSvc.UpdateTargetStatus(ctx, c.CampaignID, party.PartyID, "responded"); err != nil {
		t.Fatalf("sent→responded: %v", err)
	}
	// responded → converted is valid.
	if err := campSvc.UpdateTargetStatus(ctx, c.CampaignID, party.PartyID, "converted"); err != nil {
		t.Fatalf("responded→converted: %v", err)
	}
	// converted → sent is INVALID (terminal).
	err := campSvc.UpdateTargetStatus(ctx, c.CampaignID, party.PartyID, "sent")
	if err == nil || !domain.IsValidationError(err) {
		t.Fatalf("expected ValidationError for converted→sent, got: %v", err)
	}
}

// ─── ScanConversions ─────────────────────────────────────────────────────────

func TestCampaign_ScanConversions(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)

	// Seed party with sapo identity → customerID 301.
	partyID := seedPartyWithSapoIdentity(t, db, "Converting Customer", 301)

	// Seed an order AFTER the campaign scheduled date.
	scheduledAt := "2026-01-10T00:00:00.000Z"
	seedOrdersInCache(t, dataDir, []struct {
		orderCode  string
		customerID int64
		dateKey    int
		netRevenue int64
	}{
		{"ORD-301-A", 301, 20260115, 500000}, // after scheduled → should convert
	})

	// Create segment + campaign with scheduled_at.
	seg := &domain.Segment{Name: "Scan Seg", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyID)

	c := &domain.Campaign{
		Name:        "Scan Campaign",
		Objective:   "reactivation",
		SegmentID:   &seg.SegmentID,
		ScheduledAt: &scheduledAt,
	}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if _, err := campSvc.GenerateTargets(ctx, c.CampaignID); err != nil {
		t.Fatalf("generate targets: %v", err)
	}

	// Scan conversions — should find ORD-301-A.
	n, err := campSvc.ScanConversions(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("scan conversions: %v", err)
	}
	if n != 1 {
		t.Errorf("expected 1 conversion, got %d", n)
	}

	targets, _ := campSvc.ListTargets(ctx, c.CampaignID, "")
	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}
	tgt := targets[0]
	if tgt.Status != "converted" {
		t.Errorf("target status = %q; want converted", tgt.Status)
	}
	if tgt.ConvertedOrderCode == nil || *tgt.ConvertedOrderCode != "ORD-301-A" {
		t.Errorf("converted_order_code = %v; want ORD-301-A", tgt.ConvertedOrderCode)
	}
	if tgt.ConvertedRevenueVND == nil || *tgt.ConvertedRevenueVND != 500000 {
		t.Errorf("converted_revenue_vnd = %v; want 500000", tgt.ConvertedRevenueVND)
	}
}

func TestCampaign_ScanConversions_OrderBeforeScheduled_NoConversion(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)

	partyID := seedPartyWithSapoIdentity(t, db, "Old Order Customer", 401)

	// Order is BEFORE scheduled date — must not count as conversion.
	seedOrdersInCache(t, dataDir, []struct {
		orderCode  string
		customerID int64
		dateKey    int
		netRevenue int64
	}{
		{"ORD-401-OLD", 401, 20250101, 300000}, // before scheduled 2026-01-10
	})

	scheduledAt := "2026-01-10T00:00:00.000Z"
	seg := &domain.Segment{Name: "Seg401", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyID)

	c := &domain.Campaign{
		Name:        "No Convert Campaign",
		Objective:   "reactivation",
		SegmentID:   &seg.SegmentID,
		ScheduledAt: &scheduledAt,
	}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if _, err := campSvc.GenerateTargets(ctx, c.CampaignID); err != nil {
		t.Fatalf("generate targets: %v", err)
	}

	n, err := campSvc.ScanConversions(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("scan conversions: %v", err)
	}
	if n != 0 {
		t.Errorf("expected 0 conversions (order before scheduled_at), got %d", n)
	}

	targets, _ := campSvc.ListTargets(ctx, c.CampaignID, "")
	if targets[0].Status == "converted" {
		t.Error("target status should NOT be converted when order predates campaign")
	}
}

func TestCampaign_ScanConversions_Idempotent(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)

	partyID := seedPartyWithSapoIdentity(t, db, "Repeat Scan Customer", 501)
	scheduledAt := "2026-01-01T00:00:00.000Z"

	seedOrdersInCache(t, dataDir, []struct {
		orderCode  string
		customerID int64
		dateKey    int
		netRevenue int64
	}{
		{"ORD-501", 501, 20260115, 200000},
	})

	seg := &domain.Segment{Name: "Seg501", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyID)

	c := &domain.Campaign{
		Name:        "Idempotent Scan Campaign",
		Objective:   "winback",
		SegmentID:   &seg.SegmentID,
		ScheduledAt: &scheduledAt,
	}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if _, err := campSvc.GenerateTargets(ctx, c.CampaignID); err != nil {
		t.Fatalf("generate targets: %v", err)
	}

	n1, _ := campSvc.ScanConversions(ctx, c.CampaignID)
	n2, _ := campSvc.ScanConversions(ctx, c.CampaignID) // re-scan

	if n1 != 1 {
		t.Errorf("first scan should convert 1, got %d", n1)
	}
	if n2 != 0 {
		t.Errorf("second scan should convert 0 (idempotent), got %d", n2)
	}
}

func TestCampaign_ScanConversions_CacheEmpty_NoError(t *testing.T) {
	db, cleanup := openTestDB(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)

	party := makeParty("Cache Empty Customer", "", "")
	if err := NewPartyRepo(db).Create(ctx, party); err != nil {
		t.Fatalf("seed party: %v", err)
	}

	seg := &domain.Segment{Name: "Empty Cache Seg", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, party.PartyID)

	c := &domain.Campaign{Name: "Empty Cache Camp", Objective: "crosssell", SegmentID: &seg.SegmentID}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if _, err := campSvc.GenerateTargets(ctx, c.CampaignID); err != nil {
		t.Fatalf("generate targets: %v", err)
	}

	// No wh_order_hdr table → should return 0 conversions, no error.
	n, err := campSvc.ScanConversions(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("expected no error when cache empty, got: %v", err)
	}
	if n != 0 {
		t.Errorf("expected 0 conversions when cache empty, got %d", n)
	}
}

// ─── ROI summary ─────────────────────────────────────────────────────────────

func TestCampaign_ROI_Summary(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)

	// Three parties; one converts, two do not.
	partyA := seedPartyWithSapoIdentity(t, db, "Converter", 601)
	partyB := makeParty("Non-Converter-B", "", "")
	partyC := makeParty("Non-Converter-C", "", "")
	partyRepo := NewPartyRepo(db)
	_ = partyRepo.Create(ctx, partyB)
	_ = partyRepo.Create(ctx, partyC)

	scheduledAt := "2026-01-01T00:00:00.000Z"
	seedOrdersInCache(t, dataDir, []struct {
		orderCode  string
		customerID int64
		dateKey    int
		netRevenue int64
	}{
		{"ORD-601", 601, 20260201, 750000},
	})

	seg := &domain.Segment{Name: "ROI Seg", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyA)
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyB.PartyID)
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyC.PartyID)

	c := &domain.Campaign{
		Name:        "ROI Campaign",
		Objective:   "reactivation",
		SegmentID:   &seg.SegmentID,
		ScheduledAt: &scheduledAt,
	}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if _, err := campSvc.GenerateTargets(ctx, c.CampaignID); err != nil {
		t.Fatalf("generate targets: %v", err)
	}
	if _, err := campSvc.ScanConversions(ctx, c.CampaignID); err != nil {
		t.Fatalf("scan conversions: %v", err)
	}

	roi, err := campSvc.GetROI(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("get roi: %v", err)
	}
	if roi.TotalTargets != 3 {
		t.Errorf("total_targets = %d; want 3", roi.TotalTargets)
	}
	if roi.StatusCounts["converted"] != 1 {
		t.Errorf("converted count = %d; want 1", roi.StatusCounts["converted"])
	}
	if roi.TotalConvertedRevVND != 750000 {
		t.Errorf("total_converted_revenue_vnd = %d; want 750000", roi.TotalConvertedRevVND)
	}
}

// ─── Fix 4: manual member preserved after refresh ────────────────────────────

// TestSegmentRefresh_ManualMemberPreserved pins that a party manually added to a
// dynamic segment retains source='manual' after a rule-based refresh, even when
// that party also satisfies the rule.
func TestSegmentRefresh_ManualMemberPreserved(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	// Party 701: VIP + at_risk → matches the rule. Also manually added.
	partyID := seedPartyWithSapoIdentity(t, db, "Manual+Rule Customer", 701)
	seedInsightInCache(t, dataDir, []struct {
		customerID     int64
		valueGroup     string
		customerStatus string
		channelPref    string
	}{
		{701, "VIP", "at_risk", ""},
	})

	seg := &domain.Segment{
		Name:       "VIP At-Risk (manual member test)",
		IsDynamic:  true,
		Definition: `{"value_group":["VIP"],"customer_status":"at_risk"}`,
	}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}

	// Manually add the party before the first refresh.
	if err := svc.AddMember(ctx, seg.SegmentID, partyID); err != nil {
		t.Fatalf("add manual member: %v", err)
	}

	// Confirm manual source is stored.
	members, err := svc.ListMembers(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("list members before refresh: %v", err)
	}
	if len(members) != 1 || members[0].Source != "manual" {
		t.Fatalf("expected 1 manual member before refresh, got: %v", members)
	}

	// Refresh: rule also matches this party. The upsert must NOT downgrade 'manual' → 'rule'.
	n, err := svc.RefreshDynamicSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("refresh segment: %v", err)
	}
	if n != 1 {
		t.Errorf("expected refresh to report 1 member, got %d", n)
	}

	members, err = svc.ListMembers(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("list members after refresh: %v", err)
	}
	if len(members) != 1 {
		t.Fatalf("expected 1 member after refresh, got %d", len(members))
	}
	if members[0].PartyID != partyID {
		t.Errorf("member party_id = %q; want %q", members[0].PartyID, partyID)
	}
	// Source must remain 'manual' — not downgraded to 'rule'.
	if members[0].Source != "manual" {
		t.Errorf("member source = %q after refresh; want manual (must not be downgraded)", members[0].Source)
	}
}

// ─── Fix 5: skipped target not flipped to converted ──────────────────────────

// TestCampaign_ScanConversions_SkippedNotConverted pins that a target in the
// terminal 'skipped' state is NOT flipped to 'converted' even when a qualifying
// order exists for that party.
func TestCampaign_ScanConversions_SkippedNotConverted(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	segSvc := buildSegmentSvc(db)
	campSvc := buildCampaignSvc(db)

	partyID := seedPartyWithSapoIdentity(t, db, "Skipped Customer", 801)

	scheduledAt := "2026-01-01T00:00:00Z"
	// Order AFTER the campaign scheduled date — would convert if target were eligible.
	seedOrdersInCache(t, dataDir, []struct {
		orderCode  string
		customerID int64
		dateKey    int
		netRevenue int64
	}{
		{"ORD-801", 801, 20260115, 300000},
	})

	seg := &domain.Segment{Name: "Skipped Seg", IsDynamic: false}
	if err := segSvc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}
	_ = segSvc.AddMember(ctx, seg.SegmentID, partyID)

	c := &domain.Campaign{
		Name:        "Skipped Campaign",
		Objective:   "reactivation",
		SegmentID:   &seg.SegmentID,
		ScheduledAt: &scheduledAt,
	}
	if err := campSvc.CreateCampaign(ctx, c); err != nil {
		t.Fatalf("create campaign: %v", err)
	}
	if _, err := campSvc.GenerateTargets(ctx, c.CampaignID); err != nil {
		t.Fatalf("generate targets: %v", err)
	}

	// Move target to 'skipped' (terminal state).
	if err := campSvc.UpdateTargetStatus(ctx, c.CampaignID, partyID, "skipped"); err != nil {
		t.Fatalf("skip target: %v", err)
	}

	// ScanConversions must NOT flip the skipped target to converted.
	n, err := campSvc.ScanConversions(ctx, c.CampaignID)
	if err != nil {
		t.Fatalf("scan conversions: %v", err)
	}
	if n != 0 {
		t.Errorf("expected 0 conversions for skipped target, got %d", n)
	}

	targets, _ := campSvc.ListTargets(ctx, c.CampaignID, "")
	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}
	if targets[0].Status != "skipped" {
		t.Errorf("target status = %q; want skipped (must not be overwritten)", targets[0].Status)
	}
}

// ─── Fix 9: party with no orders not matched by days_since_last_order_gte ───

// TestSegmentRefresh_NoOrderParty_NotMatchedByDaysSinceRule pins the reactivation
// semantic: a party with NO orders in wh_order_hdr must NOT match a segment rule
// with days_since_last_order_gte, because such parties are acquisition targets,
// not reactivation candidates.
func TestSegmentRefresh_NoOrderParty_NotMatchedByDaysSinceRule(t *testing.T) {
	db, dataDir, cleanup := openTestDBWithDir(t)
	defer cleanup()

	ctx := context.Background()
	svc := buildSegmentSvc(db)

	// Party 901: has sapo identity but NO orders in wh_order_hdr.
	partyNoOrders := seedPartyWithSapoIdentity(t, db, "No-Order Customer", 901)
	// Party 902: has orders, last order 90 days ago (qualifies for ≥60-day rule).
	partyWithOrders := seedPartyWithSapoIdentity(t, db, "Old-Order Customer", 902)

	// Seed only party 902's order — party 901 intentionally has none.
	// Use a dateKey that is more than 60 days in the past from any realistic "now".
	seedOrdersInCache(t, dataDir, []struct {
		orderCode  string
		customerID int64
		dateKey    int
		netRevenue int64
	}{
		{"ORD-902-OLD", 902, 20240101, 100000}, // ~2.5 years ago
	})

	seg := &domain.Segment{
		Name:       "Inactive ≥60 days",
		IsDynamic:  true,
		Definition: `{"days_since_last_order_gte":60}`,
	}
	if err := svc.CreateSegment(ctx, seg); err != nil {
		t.Fatalf("create segment: %v", err)
	}

	n, err := svc.RefreshDynamicSegment(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("refresh segment: %v", err)
	}

	// Only party 902 (has qualifying old order) should match; party 901 (no orders) must not.
	if n != 1 {
		t.Errorf("expected 1 member (party with old order), got %d", n)
	}

	members, err := svc.ListMembers(ctx, seg.SegmentID)
	if err != nil {
		t.Fatalf("list members: %v", err)
	}
	for _, m := range members {
		if m.PartyID == partyNoOrders {
			t.Errorf("party with no orders (%s) must NOT be in segment; parties with no order history are acquisition targets, not reactivation candidates", partyNoOrders)
		}
	}
	found902 := false
	for _, m := range members {
		if m.PartyID == partyWithOrders {
			found902 = true
		}
	}
	if !found902 {
		t.Errorf("party with old order (%s) should be in segment but was not found", partyWithOrders)
	}
}

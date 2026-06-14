// Package sqlite — integration tests for Phase 04 cache repo + party seed consumer.
// All tests use real temp SQLite files with migrations applied; no mocks.
//
// Key design: openTestDB ATTACHes cache.db READ-ONLY (production behaviour).
// Tests that need to pre-populate cache.db use openCacheRW to write directly to
// the file before the Go DB is opened, so the ATTACH sees the data immediately.
//
// Test inventory:
//   TestCacheRepo_GracefulEmpty          — GetCustomerInsight returns nil when wh_* tables absent
//   TestCacheRepo_ListPartySeed_Empty    — ListPartySeed returns [] when table absent
//   TestCacheRepo_PopulatedInsight       — GetCustomerInsight returns data after seed
//   TestPartySeedConsumer_CreatesParty   — SyncParties creates crm_party + identity from seed
//   TestPartySeedConsumer_Idempotent     — SyncParties called twice → no duplicates
//   TestCacheRepo_GracefulEmpty_360      — GetParty360 (crm-only view) still works with empty cache
//   TestCacheRepo_InsightNotFound        — unknown customer_id → nil,nil
//   TestCacheRepo_ListPartySeed_Populated — all seed rows returned
//   TestCacheRepo_ActionsEmptySlice     — no actions → non-nil empty slice
package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	// registers the "sqlite" driver used by openCacheRW
	_ "modernc.org/sqlite"

	"github.com/vantt/data-integration/crm/app/internal/application"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ─── openTestDBInDir: variant that also returns the data dir path ─────────────

// openTestDBInDir opens a temporary crm.db + cache.db, applies migrations, and
// returns (DB, dataDir, cleanup).  Callers that need to write to cache.db before
// the ATTACH use openCacheRW(filepath.Join(dataDir, "cache.db")).
func openTestDBInDir(t *testing.T) (*DB, string, func()) {
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
	cleanup := func() {
		_ = db.Close()
		_ = os.RemoveAll(filepath.Join(dir, "crm.db"))
	}
	return db, dir, cleanup
}

// openCacheRW opens (or creates) cache.db at path with full read-write access.
// Used in tests to pre-populate wh_* tables before the Go DB ATTACHes it RO.
func openCacheRW(path string) (*sql.DB, error) {
	conn, err := sql.Open("sqlite", "file:"+filepath.ToSlash(path))
	if err != nil {
		return nil, err
	}
	conn.SetMaxOpenConns(1)
	if _, err := conn.Exec("PRAGMA journal_mode=WAL"); err != nil {
		_ = conn.Close()
		return nil, err
	}
	return conn, nil
}

// ─── DDL + insert helpers (write to cache.db via RW connection) ───────────────

const cacheSchemaSQL = `
CREATE TABLE IF NOT EXISTS wh_customer_insight (
	customer_key TEXT PRIMARY KEY,
	customer_id INTEGER,
	value_group TEXT, customer_status TEXT,
	next_purchase_signal TEXT, predicted_next_purchase_date TEXT,
	avg_days_between_orders REAL, avg_order_spend REAL,
	discount_sensitivity TEXT, cancel_rate REAL,
	last_purchased_sku TEXT, top_affinity_product TEXT,
	second_affinity_product TEXT, channel_preference TEXT,
	lifetime_contribution_margin REAL, is_margin_negative INTEGER,
	refreshed_at TEXT
);
CREATE TABLE IF NOT EXISTS wh_action_queue (
	action_id TEXT PRIMARY KEY,
	customer_key TEXT, action_type TEXT,
	rationale_vi TEXT, value_at_stake_vnd INTEGER,
	priority INTEGER, generated_date TEXT, refreshed_at TEXT
);
CREATE TABLE IF NOT EXISTS wh_order_hdr (
	order_id TEXT PRIMARY KEY,
	order_code TEXT, customer_id INTEGER,
	date_key INTEGER, net_revenue INTEGER,
	status TEXT, channel TEXT, item_count INTEGER,
	refreshed_at TEXT
);
CREATE TABLE IF NOT EXISTS wh_party_seed (
	customer_id INTEGER PRIMARY KEY,
	customer_key TEXT,
	seen_at TEXT
);`

// prepareCacheDB writes the wh_* schema (and optionally data) into cache.db
// at the given path via a direct RW connection, then closes it.
// The Go DB must be opened AFTER this call so ATTACH sees the tables.
func prepareCacheDB(t *testing.T, cachePath string, seedFn func(conn *sql.DB)) {
	t.Helper()
	conn, err := openCacheRW(cachePath)
	if err != nil {
		t.Fatalf("prepareCacheDB open: %v", err)
	}
	defer func() {
		if err := conn.Close(); err != nil {
			t.Fatalf("prepareCacheDB close: %v", err)
		}
	}()

	if _, err := conn.Exec(cacheSchemaSQL); err != nil {
		t.Fatalf("prepareCacheDB schema: %v", err)
	}
	if seedFn != nil {
		seedFn(conn)
	}
}

func rwInsertInsight(t *testing.T, conn *sql.DB, customerKey string, customerID int64) {
	t.Helper()
	_, err := conn.Exec(`
		INSERT INTO wh_customer_insight
		  (customer_key, customer_id, value_group, customer_status,
		   next_purchase_signal, avg_order_spend, refreshed_at)
		VALUES (?, ?, 'VIP', 'active', 'DUE_SOON', 850000, '2026-06-14T00:00:00.000Z')`,
		customerKey, customerID,
	)
	if err != nil {
		t.Fatalf("rwInsertInsight: %v", err)
	}
}

func rwInsertAction(t *testing.T, conn *sql.DB, actionID, customerKey string) {
	t.Helper()
	_, err := conn.Exec(`
		INSERT INTO wh_action_queue
		  (action_id, customer_key, action_type, rationale_vi,
		   value_at_stake_vnd, priority, generated_date, refreshed_at)
		VALUES (?, ?, 'REORDER_NUDGE', 'Khach sap den chu ky mua',
		        850000, 1, '2026-06-14', '2026-06-14T00:00:00.000Z')`,
		actionID, customerKey,
	)
	if err != nil {
		t.Fatalf("rwInsertAction: %v", err)
	}
}

func rwInsertOrder(t *testing.T, conn *sql.DB, orderID string, customerID int64, dateKey int) {
	t.Helper()
	_, err := conn.Exec(`
		INSERT INTO wh_order_hdr
		  (order_id, order_code, customer_id, date_key,
		   net_revenue, status, channel, item_count, refreshed_at)
		VALUES (?, ?, ?, ?, 850000, 'completed', 'online', 2,
		        '2026-06-14T00:00:00.000Z')`,
		orderID, fmt.Sprintf("HD%s", orderID), customerID, dateKey,
	)
	if err != nil {
		t.Fatalf("rwInsertOrder: %v", err)
	}
}

func rwInsertSeed(t *testing.T, conn *sql.DB, customerID int64, customerKey string) {
	t.Helper()
	_, err := conn.Exec(`
		INSERT INTO wh_party_seed (customer_id, customer_key, seen_at)
		VALUES (?, ?, '2026-06-14T00:00:00.000Z')`,
		customerID, customerKey,
	)
	if err != nil {
		t.Fatalf("rwInsertSeed: %v", err)
	}
}

// ─── crm.db helpers ───────────────────────────────────────────────────────────

func countParties(t *testing.T, db *DB) int {
	t.Helper()
	var n int
	if err := db.SQLDB().QueryRow("SELECT COUNT(*) FROM crm_party").Scan(&n); err != nil {
		t.Fatalf("countParties: %v", err)
	}
	return n
}

func countIdentitiesBySapoID(t *testing.T, db *DB, sapoID string) int {
	t.Helper()
	var n int
	if err := db.SQLDB().QueryRow(
		`SELECT COUNT(*) FROM crm_party_identity
		 WHERE identity_type = 'sapo_customer' AND identity_value = ?`, sapoID,
	).Scan(&n); err != nil {
		t.Fatalf("countIdentitiesBySapoID: %v", err)
	}
	return n
}

// ─── T: GetCustomerInsight — graceful empty (no wh_* tables) ─────────────────

func TestCacheRepo_GracefulEmpty(t *testing.T) {
	db, _, cleanup := openTestDBInDir(t)
	defer cleanup()

	repo := NewCacheRepo(db)
	insight, err := repo.GetCustomerInsight(context.Background(), 1001)
	if err != nil {
		t.Fatalf("expected no error when cache tables absent, got: %v", err)
	}
	if insight != nil {
		t.Fatalf("expected nil insight when cache empty, got: %+v", insight)
	}
}

// ─── T: ListPartySeed — graceful empty ───────────────────────────────────────

func TestCacheRepo_ListPartySeed_Empty(t *testing.T) {
	db, _, cleanup := openTestDBInDir(t)
	defer cleanup()

	repo := NewCacheRepo(db)
	seeds, err := repo.ListPartySeed(context.Background())
	if err != nil {
		t.Fatalf("expected no error when party_seed table absent, got: %v", err)
	}
	if len(seeds) != 0 {
		t.Fatalf("expected empty slice, got %d rows", len(seeds))
	}
}

// ─── T: GetCustomerInsight — populated ───────────────────────────────────────

func TestCacheRepo_PopulatedInsight(t *testing.T) {
	dir := t.TempDir()
	cachePath := filepath.Join(dir, "cache.db")

	const customerID int64 = 1001
	const customerKey = "key-cust-001"

	// Pre-populate cache.db before the Go DB opens it (ATTACH is RO).
	prepareCacheDB(t, cachePath, func(conn *sql.DB) {
		rwInsertInsight(t, conn, customerKey, customerID)
		rwInsertAction(t, conn, "act-001", customerKey)
		rwInsertOrder(t, conn, "ord-001", customerID, 20260601)
		rwInsertOrder(t, conn, "ord-002", customerID, 20260501)
	})

	db, err := Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	if err := MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	repo := NewCacheRepo(db)
	result, err := repo.GetCustomerInsight(context.Background(), customerID)
	if err != nil {
		t.Fatalf("GetCustomerInsight: %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil CacheInsight, got nil")
	}

	// Insight fields.
	if result.Insight == nil {
		t.Fatal("CacheInsight.Insight is nil")
	}
	if result.Insight.ValueGroup != "VIP" {
		t.Errorf("value_group = %q; want VIP", result.Insight.ValueGroup)
	}
	if result.Insight.CustomerStatus != "active" {
		t.Errorf("customer_status = %q; want active", result.Insight.CustomerStatus)
	}

	// Actions.
	if len(result.Actions) != 1 {
		t.Errorf("actions count = %d; want 1", len(result.Actions))
	}
	if len(result.Actions) > 0 && result.Actions[0].ActionType != "REORDER_NUDGE" {
		t.Errorf("action_type = %q; want REORDER_NUDGE", result.Actions[0].ActionType)
	}

	// Recent orders (most recent first by date_key DESC).
	if len(result.RecentOrders) != 2 {
		t.Errorf("recent_orders count = %d; want 2", len(result.RecentOrders))
	}
	if len(result.RecentOrders) > 0 && result.RecentOrders[0].DateKey != 20260601 {
		t.Errorf("most recent order date_key = %d; want 20260601", result.RecentOrders[0].DateKey)
	}
}

// ─── T: SyncParties — creates crm_party + identity from seed ─────────────────

func TestPartySeedConsumer_CreatesParty(t *testing.T) {
	dir := t.TempDir()
	cachePath := filepath.Join(dir, "cache.db")

	prepareCacheDB(t, cachePath, func(conn *sql.DB) {
		rwInsertSeed(t, conn, 1001, "key-cust-001")
		rwInsertSeed(t, conn, 1002, "key-cust-002")
	})

	db, err := Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	if err := MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	partyRepo := NewPartyRepo(db)
	cacheRepo := NewCacheRepo(db)
	svc := application.NewPartySeedService(cacheRepo, partyRepo)

	n, err := svc.SyncParties(context.Background(), cacheRepo)
	if err != nil {
		t.Fatalf("SyncParties: %v", err)
	}
	if n != 2 {
		t.Errorf("SyncParties returned %d; want 2", n)
	}

	if got := countParties(t, db); got != 2 {
		t.Errorf("crm_party count = %d; want 2", got)
	}
	for _, sapoID := range []string{"1001", "1002"} {
		if c := countIdentitiesBySapoID(t, db, sapoID); c != 1 {
			t.Errorf("sapo_customer identity for %s: count = %d; want 1", sapoID, c)
		}
	}
}

// ─── T: SyncParties — idempotent (run twice → no duplicates) ─────────────────

func TestPartySeedConsumer_Idempotent(t *testing.T) {
	dir := t.TempDir()
	cachePath := filepath.Join(dir, "cache.db")

	prepareCacheDB(t, cachePath, func(conn *sql.DB) {
		rwInsertSeed(t, conn, 1001, "key-cust-001")
	})

	db, err := Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	if err := MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	partyRepo := NewPartyRepo(db)
	cacheRepo := NewCacheRepo(db)
	svc := application.NewPartySeedService(cacheRepo, partyRepo)

	ctx := context.Background()
	if _, err := svc.SyncParties(ctx, cacheRepo); err != nil {
		t.Fatalf("first SyncParties: %v", err)
	}
	if _, err := svc.SyncParties(ctx, cacheRepo); err != nil {
		t.Fatalf("second SyncParties: %v", err)
	}

	if got := countParties(t, db); got != 1 {
		t.Errorf("crm_party count = %d after two runs; want 1 (idempotent)", got)
	}
	if got := countIdentitiesBySapoID(t, db, "1001"); got != 1 {
		t.Errorf("sapo_customer identity count = %d after two runs; want 1", got)
	}
}

// ─── T: crm_party_360 view still works when cache is empty ───────────────────

func TestCacheRepo_GracefulEmpty_360(t *testing.T) {
	db, _, cleanup := openTestDBInDir(t)
	defer cleanup()

	ctx := context.Background()
	party := makeParty("Cache Test", "+84901234567", "cache@test.vn")
	partyRepo := NewPartyRepo(db)
	if err := partyRepo.Create(ctx, party); err != nil {
		t.Fatalf("create party: %v", err)
	}

	// GetParty360 must succeed even when cache.db has no wh_* tables.
	profileRepo := NewProfileRepo(db)
	_, err := profileRepo.GetParty360(ctx, party.PartyID)
	if err != nil {
		t.Fatalf("GetParty360 with empty cache: %v", err)
	}
}

// ─── T: GetCustomerInsight — different customer → nil ────────────────────────

func TestCacheRepo_InsightNotFound(t *testing.T) {
	dir := t.TempDir()
	cachePath := filepath.Join(dir, "cache.db")

	prepareCacheDB(t, cachePath, func(conn *sql.DB) {
		rwInsertInsight(t, conn, "key-cust-001", 1001)
	})

	db, err := Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	if err := MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	repo := NewCacheRepo(db)
	result, err := repo.GetCustomerInsight(context.Background(), 9999)
	if err != nil {
		t.Fatalf("unexpected error for unknown customer: %v", err)
	}
	if result != nil {
		t.Errorf("expected nil for unknown customer, got: %+v", result)
	}
}

// ─── T: ListPartySeed — returns all rows ─────────────────────────────────────

func TestCacheRepo_ListPartySeed_Populated(t *testing.T) {
	dir := t.TempDir()
	cachePath := filepath.Join(dir, "cache.db")

	prepareCacheDB(t, cachePath, func(conn *sql.DB) {
		rwInsertSeed(t, conn, 2001, "key-2001")
		rwInsertSeed(t, conn, 2002, "key-2002")
	})

	db, err := Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	if err := MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	repo := NewCacheRepo(db)
	seeds, err := repo.ListPartySeed(context.Background())
	if err != nil {
		t.Fatalf("ListPartySeed: %v", err)
	}
	if len(seeds) != 2 {
		t.Errorf("seed count = %d; want 2", len(seeds))
	}

	byID := make(map[int64]domain.PartySeed)
	for _, s := range seeds {
		byID[s.CustomerID] = s
	}
	if byID[2001].CustomerKey != "key-2001" {
		t.Errorf("customer_key for 2001 = %q; want key-2001", byID[2001].CustomerKey)
	}
	if byID[2002].CustomerKey != "key-2002" {
		t.Errorf("customer_key for 2002 = %q; want key-2002", byID[2002].CustomerKey)
	}
}

// ─── T: Actions non-nil empty slice when no rows ─────────────────────────────

func TestCacheRepo_ActionsEmptySlice(t *testing.T) {
	dir := t.TempDir()
	cachePath := filepath.Join(dir, "cache.db")

	// Insert insight but no actions.
	prepareCacheDB(t, cachePath, func(conn *sql.DB) {
		rwInsertInsight(t, conn, "key-cust-001", 1001)
	})

	db, err := Open(dir)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()
	if err := MigrateUp(db); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	repo := NewCacheRepo(db)
	result, err := repo.GetCustomerInsight(context.Background(), 1001)
	if err != nil {
		t.Fatalf("GetCustomerInsight: %v", err)
	}
	if result == nil {
		t.Fatal("expected non-nil CacheInsight")
	}
	if result.Actions == nil {
		t.Error("Actions must be non-nil empty slice, got nil")
	}
	if len(result.Actions) != 0 {
		t.Errorf("expected 0 actions, got %d", len(result.Actions))
	}
}

// ─── compile-time interface check ────────────────────────────────────────────

var _ interface {
	GetCustomerInsight(ctx context.Context, customerID int64) (*domain.CacheInsight, error)
	ListPartySeed(ctx context.Context) ([]domain.PartySeed, error)
} = (*CacheRepo)(nil)

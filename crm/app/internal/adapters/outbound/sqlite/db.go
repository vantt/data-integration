// Package sqlite implements the outbound SQLite adapter for the CRM.
// Opens crm.db (WAL, read-write) and ATTACHes cache.db (read-only).
// Uses modernc.org/sqlite — pure Go, CGO_ENABLED=0 compatible.
package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	// registers driver name "sqlite" (pure-Go, no CGO required)
	_ "modernc.org/sqlite"
)

// DB wraps the single *sql.DB connection to crm.db (with cache.db ATTACHed).
type DB struct {
	conn *sql.DB
}

// Open initialises crm.db with WAL pragmas, ensures cache.db exists, and ATTACHes it read-only.
// dataDir is the directory that holds both crm.db and cache.db.
func Open(dataDir string) (*DB, error) {
	if err := os.MkdirAll(dataDir, 0o755); err != nil {
		return nil, fmt.Errorf("sqlite: create data dir: %w", err)
	}

	crmPath := filepath.Join(dataDir, "crm.db")

	// DSN pragmas applied at connection open time (modernc sqlite DSN style).
	// journal_mode=WAL must be set before any write; busy_timeout prevents immediate SQLITE_BUSY.
	dsn := fmt.Sprintf(
		"file:%s?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)&_pragma=foreign_keys(1)&_pragma=synchronous(NORMAL)",
		crmPath,
	)

	conn, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("sqlite: open crm.db: %w", err)
	}

	// SQLite WAL works best with a single writer connection; cap pool to 1.
	conn.SetMaxOpenConns(1)
	conn.SetMaxIdleConns(1)

	if err := conn.Ping(); err != nil {
		conn.Close()
		return nil, fmt.Errorf("sqlite: ping crm.db: %w", err)
	}

	cachePath := filepath.Join(dataDir, "cache.db")

	// Guard: single quotes in the path would break the ATTACH SQL literal.
	if strings.Contains(cachePath, "'") {
		conn.Close()
		return nil, fmt.Errorf("sqlite: cache.db path must not contain single quotes: %s", cachePath)
	}

	if err := ensureCacheDB(cachePath); err != nil {
		conn.Close()
		return nil, fmt.Errorf("sqlite: ensure cache.db: %w", err)
	}

	// ATTACH cache.db as read-only schema alias "cache".
	// Use forward slashes in the URI so SQLite parses it correctly on all platforms.
	cacheURI := "file:" + filepath.ToSlash(cachePath) + "?mode=ro"
	attachSQL := fmt.Sprintf(`ATTACH DATABASE '%s' AS cache`, cacheURI)
	if _, err := conn.Exec(attachSQL); err != nil {
		conn.Close()
		return nil, fmt.Errorf("sqlite: attach cache.db: %w", err)
	}

	return &DB{conn: conn}, nil
}

// Close releases the database connection.
func (db *DB) Close() error {
	return db.conn.Close()
}

// Ping checks that the primary crm.db connection is alive.
func (db *DB) Ping(ctx context.Context) error {
	return db.conn.PingContext(ctx)
}

// CacheAttached returns true if the cache schema is attached and readable.
// Uses COUNT(*) so the query always returns a row regardless of sqlite_master contents.
func (db *DB) CacheAttached(ctx context.Context) bool {
	var n int
	err := db.conn.QueryRowContext(ctx, "SELECT COUNT(*) FROM cache.sqlite_master").Scan(&n)
	return err == nil
}

// SQLDB returns the underlying *sql.DB (needed by the migrate adapter).
func (db *DB) SQLDB() *sql.DB {
	return db.conn
}

// ensureCacheDB creates an empty SQLite file at path if it does not already exist.
// This prevents ATTACH from failing when the Python reverse-ETL hasn't run yet.
func ensureCacheDB(path string) error {
	if _, err := os.Stat(path); err == nil {
		return nil // already exists
	}

	tmp, err := sql.Open("sqlite", "file:"+filepath.ToSlash(path))
	if err != nil {
		return fmt.Errorf("create cache.db: %w", err)
	}

	// Ping to trigger file creation, then set WAL + synchronous so Python sync can open it consistently.
	if err := tmp.Ping(); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("ping cache.db: %w", err)
	}
	if _, err := tmp.Exec("PRAGMA journal_mode=WAL"); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("cache.db WAL: %w", err)
	}
	if _, err := tmp.Exec("PRAGMA synchronous=NORMAL"); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("cache.db synchronous: %w", err)
	}

	if err := tmp.Close(); err != nil {
		return fmt.Errorf("cache.db close: %w", err)
	}
	return nil
}

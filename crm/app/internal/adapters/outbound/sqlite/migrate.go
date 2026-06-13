// Package sqlite — migration runner using golang-migrate with embedded SQL files.
package sqlite

import (
	"errors"
	"fmt"

	"github.com/golang-migrate/migrate/v4"
	migratesqlite "github.com/golang-migrate/migrate/v4/database/sqlite"
	"github.com/golang-migrate/migrate/v4/source/iofs"

	"github.com/vantt/data-integration/crm/migrations"
)

// MigrateUp applies all pending UP migrations from the embedded SQL files.
// Safe to call on every startup — golang-migrate is idempotent (tracks applied versions).
func MigrateUp(db *DB) error {
	m, err := newMigrate(db)
	if err != nil {
		return err
	}
	if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return fmt.Errorf("migrate up: %w", err)
	}
	return nil
}

// MigrateDown rolls back the most recent migration step.
func MigrateDown(db *DB) error {
	m, err := newMigrate(db)
	if err != nil {
		return err
	}
	if err := m.Steps(-1); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return fmt.Errorf("migrate down: %w", err)
	}
	return nil
}

// newMigrate wires up the iofs source (embedded SQL) with the sqlite database driver.
func newMigrate(db *DB) (*migrate.Migrate, error) {
	src, err := iofs.New(migrations.FS, ".")
	if err != nil {
		return nil, fmt.Errorf("migrate iofs source: %w", err)
	}

	// golang-migrate sqlite driver wraps the existing *sql.DB connection.
	driver, err := migratesqlite.WithInstance(db.SQLDB(), &migratesqlite.Config{})
	if err != nil {
		return nil, fmt.Errorf("migrate sqlite driver: %w", err)
	}

	m, err := migrate.NewWithInstance("iofs", src, "crm", driver)
	if err != nil {
		return nil, fmt.Errorf("migrate init: %w", err)
	}
	return m, nil
}

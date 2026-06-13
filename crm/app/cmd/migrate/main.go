// Command migrate: thin wrapper around golang-migrate for crm.db.
// Uses embedded SQL files (no external migrate CLI needed).
//
// Usage:
//
//	go run ./app/cmd/migrate up
//	go run ./app/cmd/migrate down
//	go run ./app/cmd/migrate version
package main

import (
	"errors"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/golang-migrate/migrate/v4"
	migratesqlite "github.com/golang-migrate/migrate/v4/database/sqlite"
	"github.com/golang-migrate/migrate/v4/source/iofs"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite"
	"github.com/vantt/data-integration/crm/migrations"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: migrate <up|down|version>")
		os.Exit(1)
	}
	cmd := os.Args[1]

	dataDir := os.Getenv("CRM_DATA_DIR")
	if dataDir == "" {
		dataDir = filepath.Join(".", "data")
	}

	db, err := sqlite.Open(dataDir)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	defer db.Close()

	src, err := iofs.New(migrations.FS, ".")
	if err != nil {
		log.Fatalf("iofs source: %v", err)
	}

	driver, err := migratesqlite.WithInstance(db.SQLDB(), &migratesqlite.Config{})
	if err != nil {
		log.Fatalf("migrate driver: %v", err)
	}

	m, err := migrate.NewWithInstance("iofs", src, "crm", driver)
	if err != nil {
		log.Fatalf("migrate init: %v", err)
	}

	switch cmd {
	case "up":
		if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
			log.Fatalf("migrate up: %v", err)
		}
		v, dirty, _ := m.Version()
		fmt.Printf("migrate up OK — version %d dirty=%v\n", v, dirty)

	case "down":
		if err := m.Steps(-1); err != nil && !errors.Is(err, migrate.ErrNoChange) {
			log.Fatalf("migrate down: %v", err)
		}
		v, dirty, verr := m.Version()
		if errors.Is(verr, migrate.ErrNilVersion) {
			fmt.Println("migrate down OK — at base (no version)")
		} else {
			fmt.Printf("migrate down OK — version %d dirty=%v\n", v, dirty)
		}

	case "version":
		v, dirty, err := m.Version()
		if errors.Is(err, migrate.ErrNilVersion) {
			fmt.Println("no migrations applied")
		} else if err != nil {
			log.Fatalf("version: %v", err)
		} else {
			fmt.Printf("version %d dirty=%v\n", v, dirty)
		}

	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s (use up|down|version)\n", cmd)
		os.Exit(1)
	}
}

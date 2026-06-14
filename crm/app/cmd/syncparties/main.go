// Command syncparties reads wh_party_seed from cache.db (read-only) and upserts
// crm_party + sapo_customer identity rows into crm.db (read-write).
//
// This enforces the 1-writer rule:
//   - Python writes ONLY cache.db (reverse-ETL).
//   - Go writes ONLY crm.db (this command).
//
// Usage:
//
//	syncparties [-data <dir>]
//
// Environment:
//
//	CRM_DATA_DIR   directory containing crm.db and cache.db (default: ./data)
package main

import (
	"context"
	"flag"
	"log"
	"os"
	"path/filepath"
	"time"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite"
	"github.com/vantt/data-integration/crm/app/internal/application"
)

func main() {
	dataDir := flag.String("data", getEnv("CRM_DATA_DIR", filepath.Join(".", "data")), "directory containing crm.db and cache.db")
	flag.Parse()

	log.Printf("syncparties: data dir = %s", *dataDir)

	db, err := sqlite.Open(*dataDir)
	if err != nil {
		log.Fatalf("syncparties: open db: %v", err)
	}
	defer db.Close()

	// Self-migrate crm.db so the command is safe to run before the server.
	if err := sqlite.MigrateUp(db); err != nil {
		log.Fatalf("syncparties: migrate: %v", err)
	}

	partyRepo := sqlite.NewPartyRepo(db)
	cacheRepo := sqlite.NewCacheRepo(db)
	svc := application.NewPartySeedService(cacheRepo, partyRepo)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	n, err := svc.SyncParties(ctx, cacheRepo)
	if err != nil {
		log.Fatalf("syncparties: sync: %v", err)
	}
	log.Printf("syncparties: done — %d parties upserted", n)
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

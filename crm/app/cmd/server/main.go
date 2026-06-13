// Command server starts the CRM HTTP server.
// Self-migrates crm.db on startup; ATTACHes cache.db read-only.
// CGO_ENABLED=0 — uses modernc.org/sqlite (pure Go).
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	inboundhttp "github.com/vantt/data-integration/crm/app/internal/adapters/inbound/http"
	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite"
	"github.com/vantt/data-integration/crm/app/internal/application"
)

func main() {
	dataDir := getEnv("CRM_DATA_DIR", filepath.Join(".", "data"))
	port := getEnv("CRM_PORT", "8090")

	// Open crm.db (WAL) + ATTACH cache.db (read-only).
	db, err := sqlite.Open(dataDir)
	if err != nil {
		log.Fatalf("db open: %v", err)
	}
	defer db.Close()

	// Self-migrate on startup — idempotent, safe to re-run.
	if err := sqlite.MigrateUp(db); err != nil {
		log.Fatalf("migrate up: %v", err)
	}
	log.Println("migrations applied")

	// Repositories and services.
	partyRepo := sqlite.NewPartyRepo(db)
	dedupRepo := sqlite.NewDedupRepo(db)
	mergeService := application.NewMergeService(partyRepo, dedupRepo)

	// Chi router.
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/healthz", inboundhttp.HealthHandler(db))

	// Dedup endpoints.
	dedupHandler := inboundhttp.NewDedupHandler(dedupRepo, mergeService)
	dedupHandler.RegisterRoutes(r)

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%s", port),
		Handler:      r,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown on SIGINT / SIGTERM.
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("CRM server listening on :%s", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server: %v", err)
		}
	}()

	<-quit
	log.Println("shutting down...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("shutdown: %v", err)
	}
	log.Println("stopped")
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

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
	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web"
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

	// Customer 360 repos + service.
	profileRepo := sqlite.NewProfileRepo(db)
	customFieldRepo := sqlite.NewCustomFieldRepo(db)
	tagRepo := sqlite.NewTagRepo(db)
	noteRepo := sqlite.NewNoteRepo(db)
	profileSvc := application.NewProfileService(profileRepo, customFieldRepo, tagRepo, noteRepo)

	// Chi router.
	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/healthz", inboundhttp.HealthHandler(db))

	// Dedup endpoints.
	dedupHandler := inboundhttp.NewDedupHandler(dedupRepo, mergeService)
	dedupHandler.RegisterRoutes(r)

	// Customer 360 endpoints.
	c360Handler := inboundhttp.NewCustomer360Handler(profileSvc, profileSvc, profileSvc, profileSvc, profileSvc, partyRepo)
	c360Handler.RegisterRoutes(r)

	// Phase 04 — cache insight endpoint (GET /api/parties/{id}/insight).
	cacheRepo := sqlite.NewCacheRepo(db)
	insightHandler := inboundhttp.NewInsightHandler(partyRepo, cacheRepo)
	insightHandler.RegisterRoutes(r)

	// Phase 05 — activity, task, conversation/inbox + Messenger ingest.
	activityRepo := sqlite.NewActivityRepo(db)
	activitySvc := application.NewActivityService(activityRepo)
	activityHandler := inboundhttp.NewActivityHandler(activitySvc, activitySvc)
	activityHandler.RegisterRoutes(r)

	taskRepo := sqlite.NewTaskRepo(db)
	taskSvc := application.NewTaskService(taskRepo, partyRepo, cacheRepo)
	taskHandler := inboundhttp.NewTaskHandler(taskSvc, taskSvc, taskSvc)
	taskHandler.RegisterRoutes(r)

	convRepo := sqlite.NewConversationRepo(db)
	convSvc := application.NewConversationService(convRepo, partyRepo)
	convHandler := inboundhttp.NewConversationHandler(convSvc, convSvc, convSvc)
	convHandler.RegisterRoutes(r)

	// Phase 06 — segments + reactivation campaigns.
	segmentRepo := sqlite.NewSegmentRepo(db)
	segmentSvc := application.NewSegmentService(segmentRepo, db.SQLDB())
	segmentHandler := inboundhttp.NewSegmentHandler(segmentSvc, segmentSvc, segmentSvc)
	segmentHandler.RegisterRoutes(r)

	campaignRepo := sqlite.NewCampaignRepo(db)
	campaignSvc := application.NewCampaignService(campaignRepo, segmentRepo, partyRepo, db.SQLDB())
	campaignHandler := inboundhttp.NewCampaignHandler(campaignSvc, campaignSvc)
	campaignHandler.RegisterRoutes(r)

	// Web UI adapter (templ + HTMX) — mounted at / (JSON API stays under /api).
	// Auth: DEFERRED — LAN-trust only.
	appUserRepo := sqlite.NewAppUserRepo(db)
	webDeps := &web.Deps{
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
		// Shared modals (M02, M04).
		PartyCreator:  partyRepo,
		OwnerAssigner: profileSvc,
		// Management screens (S08–S13).
		Segments:    segmentSvc,
		Campaigns:   campaignSvc,
		SettingsMgr: profileSvc,
	}
	web.Mount(r, webDeps)

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

// Package http — Admin handler: POST /admin/refresh
//
// Lets an external orchestrator (Dagster) trigger the reverse-ETL + syncparties
// on demand, after the warehouse serving layer updates. The handler depends only
// on the narrow Refresher port (dependency-inversion) so it is unit-testable
// without shelling out — tests inject a fake Refresher.
//
// Behaviour:
//   - Single-flight: only ONE refresh runs at a time. A second concurrent request
//     returns 409 {"status":"busy"} immediately (no queueing/blocking).
//   - Auth (defense-in-depth, LAN-trust): if CRM_REFRESH_TOKEN is set the request
//     must carry a matching X-Refresh-Token header, else 401. If unset, the
//     endpoint is open (a warning is logged once at construction).
//   - Synchronous: runs the refresh and waits, returning 200 on success / 500 on
//     failure. A context timeout caps the run as a safety net.
package http

import (
	"context"
	"log"
	"net/http"
	"sync/atomic"
	"time"

	"github.com/go-chi/chi/v5"
)

// refreshHeaderName is the header carrying the shared secret when CRM_REFRESH_TOKEN is set.
const refreshHeaderName = "X-Refresh-Token"

// defaultRefreshTimeout caps a single refresh run. The sync is ~seconds for ~7.5k
// rows; the generous cap only guards against a wedged subprocess.
const defaultRefreshTimeout = 15 * time.Minute

// RefreshResult summarises one refresh run. Returned by the Refresher port and
// merged into the JSON response.
type RefreshResult struct {
	StartedAt  time.Time `json:"started_at"`
	FinishedAt time.Time `json:"finished_at"`
	DurationMs int64     `json:"duration_ms"`
	Output     string    `json:"output,omitempty"` // tail of combined stdout/stderr
}

// Refresher is the outbound port the admin handler depends on. The concrete
// implementation (shell_refresher) runs /app/refresh.sh; tests use a fake.
type Refresher interface {
	Refresh(ctx context.Context) (RefreshResult, error)
}

// AdminHandler serves POST /admin/refresh.
type AdminHandler struct {
	refresher Refresher
	token     string        // CRM_REFRESH_TOKEN; empty = unprotected
	timeout   time.Duration // safety cap per run
	running   int32         // atomic single-flight guard (0=idle, 1=running)
}

// NewAdminHandler constructs the handler. An empty token leaves the endpoint
// unprotected and logs a one-time warning.
func NewAdminHandler(refresher Refresher, token string) *AdminHandler {
	if token == "" {
		log.Printf("admin: WARNING CRM_REFRESH_TOKEN unset — POST /admin/refresh is UNPROTECTED (LAN-trust only)")
	}
	return &AdminHandler{
		refresher: refresher,
		token:     token,
		timeout:   defaultRefreshTimeout,
	}
}

// RegisterRoutes mounts admin routes on the given chi router.
func (h *AdminHandler) RegisterRoutes(r chi.Router) {
	r.Post("/admin/refresh", h.refresh)
}

// POST /admin/refresh
func (h *AdminHandler) refresh(w http.ResponseWriter, r *http.Request) {
	// Auth: if a token is configured, require a matching header.
	if h.token != "" && r.Header.Get(refreshHeaderName) != h.token {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"status": "unauthorized"})
		return
	}

	// Single-flight: atomically claim the running slot; reject if already taken.
	if !atomic.CompareAndSwapInt32(&h.running, 0, 1) {
		writeJSON(w, http.StatusConflict, map[string]string{"status": "busy"})
		return
	}
	defer atomic.StoreInt32(&h.running, 0)

	ctx, cancel := context.WithTimeout(r.Context(), h.timeout)
	defer cancel()

	log.Printf("admin: refresh started")
	res, err := h.refresher.Refresh(ctx)
	if err != nil {
		log.Printf("admin: refresh failed: %v", err)
		writeJSON(w, http.StatusInternalServerError, map[string]any{
			"status":      "error",
			"error":       err.Error(),
			"started_at":  res.StartedAt,
			"finished_at": res.FinishedAt,
			"duration_ms": res.DurationMs,
			"output":      res.Output,
		})
		return
	}

	log.Printf("admin: refresh ok in %dms", res.DurationMs)
	writeJSON(w, http.StatusOK, map[string]any{
		"status":      "ok",
		"started_at":  res.StartedAt,
		"finished_at": res.FinishedAt,
		"duration_ms": res.DurationMs,
		"output":      res.Output,
	})
}

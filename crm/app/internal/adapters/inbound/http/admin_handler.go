// Package http — Admin handler: POST /admin/refresh and GET /admin/refresh/status
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
//   - Fire-and-forget: the POST starts the refresh in a background goroutine and
//     returns 202 {"status":"accepted"} IMMEDIATELY — it does not wait. Callers
//     poll GET /admin/refresh/status to observe the last run's outcome.
package http

import (
	"context"
	"log"
	"net/http"
	"sync"
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

// refreshState captures the last-run state, surfaced via GET /admin/refresh/status.
// Because the POST is fire-and-forget, this is the only window ops/Dagster have
// onto the outcome of a triggered run.
type refreshState struct {
	State      string `json:"state"` // idle | running | ok | error
	StartedAt  string `json:"started_at,omitempty"`
	FinishedAt string `json:"finished_at,omitempty"`
	DurationMs int64  `json:"duration_ms,omitempty"`
	Error      string `json:"error,omitempty"`
	OutputTail string `json:"output_tail,omitempty"`
}

// AdminHandler serves POST /admin/refresh and GET /admin/refresh/status.
type AdminHandler struct {
	refresher Refresher
	token     string        // CRM_REFRESH_TOKEN; empty = unprotected
	timeout   time.Duration // safety cap per run

	mu      sync.Mutex   // guards running + state
	running bool         // single-flight guard (true while a goroutine is in-flight)
	state   refreshState // last-run state
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
		state:     refreshState{State: "idle"},
	}
}

// RegisterRoutes mounts admin routes on the given chi router.
func (h *AdminHandler) RegisterRoutes(r chi.Router) {
	r.Post("/admin/refresh", h.refresh)
	r.Get("/admin/refresh/status", h.status)
}

// POST /admin/refresh — fire-and-forget. Claims the single-flight slot, launches
// the refresh on a background goroutine, and returns 202 immediately.
func (h *AdminHandler) refresh(w http.ResponseWriter, r *http.Request) {
	// Auth: if a token is configured, require a matching header.
	if h.token != "" && r.Header.Get(refreshHeaderName) != h.token {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"status": "unauthorized"})
		return
	}

	startedAt := time.Now()

	// Single-flight: claim the running slot under the lock; reject if already taken.
	h.mu.Lock()
	if h.running {
		h.mu.Unlock()
		writeJSON(w, http.StatusConflict, map[string]string{"status": "busy"})
		return
	}
	h.running = true
	h.state = refreshState{State: "running", StartedAt: startedAt.Format(time.RFC3339Nano)}
	h.mu.Unlock()

	// Launch the refresh on a detached goroutine. CRITICAL: use context.Background()
	// (with the timeout cap) — NOT the request context. The request context is
	// cancelled the moment the 202 is written, which would kill the sync instantly.
	go h.runRefresh(startedAt)

	log.Printf("admin: refresh accepted (running async)")
	writeJSON(w, http.StatusAccepted, map[string]any{
		"status":     "accepted",
		"started_at": startedAt,
	})
}

// runRefresh executes the refresh and records the outcome. It owns the running
// flag for its lifetime and clears it on completion.
func (h *AdminHandler) runRefresh(startedAt time.Time) {
	ctx, cancel := context.WithTimeout(context.Background(), h.timeout)
	defer cancel()

	log.Printf("admin: refresh started")
	res, err := h.refresher.Refresh(ctx)

	h.mu.Lock()
	defer h.mu.Unlock()
	h.running = false
	if err != nil {
		log.Printf("admin: refresh failed: %v", err)
		h.state = refreshState{
			State:      "error",
			StartedAt:  startedAt.Format(time.RFC3339Nano),
			FinishedAt: time.Now().Format(time.RFC3339Nano),
			DurationMs: res.DurationMs,
			Error:      err.Error(),
			OutputTail: res.Output,
		}
		return
	}
	log.Printf("admin: refresh ok in %dms", res.DurationMs)
	h.state = refreshState{
		State:      "ok",
		StartedAt:  startedAt.Format(time.RFC3339Nano),
		FinishedAt: res.FinishedAt.Format(time.RFC3339Nano),
		DurationMs: res.DurationMs,
		OutputTail: res.Output,
	}
}

// GET /admin/refresh/status — returns the last-run state JSON. Open for read
// (no token) so ops can poll freely; it exposes no secrets.
func (h *AdminHandler) status(w http.ResponseWriter, r *http.Request) {
	h.mu.Lock()
	st := h.state
	h.mu.Unlock()
	writeJSON(w, http.StatusOK, st)
}

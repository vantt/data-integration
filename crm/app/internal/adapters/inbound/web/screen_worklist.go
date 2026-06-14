// Package web — S01 Worklist screen handler.
// Inbound adapter: reads from ActionQueueReader + TaskQuerier. No business logic.
package web

import (
	"html"
	"log"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

func init() {
	register(func(r chi.Router, d *Deps) {
		r.Get("/", d.handleWorklist)
		r.Get("/worklist/fragment", d.handleWorklistFragment)
		r.Patch("/tasks/{taskID}/done", d.handleMarkTaskDone)
	})
}

// handleWorklist serves GET / — the full worklist page.
func (d *Deps) handleWorklist(w http.ResponseWriter, r *http.Request) {
	actions, tasks, refreshedAt, isStale := d.loadWorklistData(r)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.WorklistPage(actions, tasks, refreshedAt, isStale).Render(r.Context(), w); err != nil {
		log.Printf("worklist: render page: %v", err)
	}
}

// handleWorklistFragment serves GET /worklist/fragment — the HTMX refresh target.
func (d *Deps) handleWorklistFragment(w http.ResponseWriter, r *http.Request) {
	actions, tasks, refreshedAt, isStale := d.loadWorklistData(r)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.WorklistFragment(actions, tasks, refreshedAt, isStale).Render(r.Context(), w); err != nil {
		log.Printf("worklist: render fragment: %v", err)
	}
}

// handleMarkTaskDone serves PATCH /tasks/{taskID}/done — marks a task done via checkbox.
// Returns the updated task-row HTML fragment (HTMX swaps it in place).
func (d *Deps) handleMarkTaskDone(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")
	if err := d.TaskWriter.TransitionStatus(r.Context(), taskID, "done"); err != nil {
		log.Printf("worklist: mark done %s: %v", taskID, err)
		http.Error(w, "failed to update task", http.StatusInternalServerError)
		return
	}
	// Return a minimal done-row fragment so HTMX can swap it.
	task, err := d.Tasks.GetTask(r.Context(), taskID)
	if err != nil || task == nil {
		// Fallback: return a simple done indicator.
		// html.EscapeString prevents XSS via a crafted taskID path segment.
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write([]byte(`<div class="task-row done" id="task-` + html.EscapeString(taskID) + `"><span class="text-muted">✓ Đã hoàn thành</span></div>`))
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.TaskDoneRow(*task).Render(r.Context(), w); err != nil {
		log.Printf("worklist: render done row: %v", err)
	}
}

// loadWorklistData fetches actions + open tasks and computes freshness.
func (d *Deps) loadWorklistData(r *http.Request) (
	actions []domain.ActionQueueItem,
	tasks []domain.Task,
	refreshedAt string,
	isStale bool,
) {
	actions, err := d.ActionQueue.ListAllActionQueue(r.Context())
	if err != nil {
		log.Printf("worklist: list actions: %v", err)
		actions = []domain.ActionQueueItem{}
	}

	tasks, err = d.Tasks.ListTasks(r.Context(), "", "open")
	if err != nil {
		log.Printf("worklist: list tasks: %v", err)
		tasks = []domain.Task{}
	}

	// Determine freshness from the first action's RefreshedAt field.
	if len(actions) > 0 && actions[0].RefreshedAt != "" {
		refreshedAt = FormatICT(actions[0].RefreshedAt)
		isStale = isCacheStale(actions[0].RefreshedAt)
	}
	return
}

// isCacheStale returns true when the UTC ISO-8601 timestamp is older than 24h.
func isCacheStale(utcISO string) bool {
	layouts := []string{
		"2006-01-02T15:04:05.000Z",
		"2006-01-02T15:04:05Z",
		"2006-01-02",
	}
	for _, l := range layouts {
		if t, err := time.Parse(l, utcISO); err == nil {
			return time.Since(t) > 24*time.Hour
		}
	}
	return false
}

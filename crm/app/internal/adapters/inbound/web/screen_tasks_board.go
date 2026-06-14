// Package web — S07 Tasks Board screen handler.
// Inbound adapter: reads/writes via TaskQuerier, TaskWriter, TaskCreator.
// No business logic here — delegates to application.TaskService.
package web

import (
	"log"
	"net/http"
	"strings"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/adapters/inbound/web/templates"
	"github.com/vantt/data-integration/crm/app/internal/domain"
)

func init() {
	register(func(r chi.Router, d *Deps) {
		// S07 — Tasks board (full page).
		r.Get("/tasks", d.handleTasksBoard)

		// M05 — Create task modal + submit.
		r.Get("/tasks/modal/create", d.handleModalCreateTask)
		r.Post("/tasks", d.handleCreateTask)

		// Task status transition (HTMX PATCH from board card).
		r.Patch("/tasks/{taskID}/status", d.handleTaskStatusTransition)

		// Generate tasks from action queue.
		r.Post("/tasks/generate", d.handleGenerateTasksFromQueue)
	})
}

// handleTasksBoard serves GET /tasks — S07 full page.
func (d *Deps) handleTasksBoard(w http.ResponseWriter, r *http.Request) {
	assignee := r.URL.Query().Get("assignee")
	statusFilter := r.URL.Query().Get("status")

	// When no explicit status filter, show all statuses for the board.
	tasks, err := d.Tasks.ListTasks(r.Context(), assignee, statusFilter)
	if err != nil {
		log.Printf("tasks board: list: %v", err)
		tasks = []domain.Task{}
	}

	// Group by status for the kanban columns.
	grouped := groupTasksByStatus(tasks)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.TasksBoardPage(grouped, assignee, statusFilter).Render(r.Context(), w); err != nil {
		log.Printf("tasks board: render: %v", err)
	}
}

// handleModalCreateTask serves GET /tasks/modal/create — M05 empty form fragment.
func (d *Deps) handleModalCreateTask(w http.ResponseWriter, r *http.Request) {
	partyID := r.URL.Query().Get("party_id") // optional pre-fill from Customer 360
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := templates.ModalCreateTask(partyID).Render(r.Context(), w); err != nil {
		log.Printf("modal create task: render: %v", err)
	}
}

// handleCreateTask serves POST /tasks — M05 submit; creates a new task.
func (d *Deps) handleCreateTask(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	title := strings.TrimSpace(r.FormValue("title"))
	if title == "" {
		http.Error(w, "title required", http.StatusBadRequest)
		return
	}

	t := &domain.Task{
		Title:       title,
		Description: strings.TrimSpace(r.FormValue("description")),
		Status:      "open",
		Source:      "manual",
	}

	// Optional fields.
	if dueAt := strings.TrimSpace(r.FormValue("due_at")); dueAt != "" {
		t.DueAt = &dueAt
	}
	if partyID := strings.TrimSpace(r.FormValue("party_id")); partyID != "" {
		t.PartyID = &partyID
	}
	if assignee := strings.TrimSpace(r.FormValue("assignee_user_id")); assignee != "" {
		t.AssigneeUserID = &assignee
	}

	if err := d.TaskCreator.CreateTask(r.Context(), t); err != nil {
		log.Printf("create task: %v", err)
		http.Error(w, "failed to create task", http.StatusInternalServerError)
		return
	}

	// Close modal and redirect to board to show new task.
	w.Header().Set("HX-Trigger", `{"closeModal":true}`)
	w.Header().Set("HX-Redirect", "/tasks")
	w.WriteHeader(http.StatusOK)
}

// handleTaskStatusTransition serves PATCH /tasks/{taskID}/status — board card status update.
func (d *Deps) handleTaskStatusTransition(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "taskID")
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	newStatus := strings.TrimSpace(r.FormValue("status"))
	if newStatus == "" {
		http.Error(w, "status required", http.StatusBadRequest)
		return
	}
	if err := d.TaskWriter.TransitionStatus(r.Context(), taskID, newStatus); err != nil {
		log.Printf("task status transition %s→%s: %v", taskID, newStatus, err)
		http.Error(w, "failed to transition", http.StatusInternalServerError)
		return
	}
	// Refresh the whole board so the card moves column.
	w.Header().Set("HX-Redirect", "/tasks")
	w.WriteHeader(http.StatusOK)
}

// handleGenerateTasksFromQueue serves POST /tasks/generate — creates tasks from action queue.
// Returns a 200 with a count fragment; graceful-empty if cache absent (returns 0, no error).
func (d *Deps) handleGenerateTasksFromQueue(w http.ResponseWriter, r *http.Request) {
	if d.TaskGen == nil {
		// TaskGen not wired (e.g. in test fixtures); redirect gracefully.
		w.Header().Set("HX-Redirect", "/tasks")
		w.WriteHeader(http.StatusOK)
		return
	}
	count, err := d.TaskGen.GenerateTasksFromActionQueue(r.Context())
	if err != nil {
		log.Printf("generate tasks from queue: %v", err)
		// Non-fatal: still redirect to board.
	}
	log.Printf("generate tasks from queue: created %d tasks", count)
	// Redirect to board so the new tasks show up.
	w.Header().Set("HX-Redirect", "/tasks")
	w.WriteHeader(http.StatusOK)
}

// ── local helpers ─────────────────────────────────────────────────────────────

// groupTasksByStatus partitions tasks into open/doing/done/cancelled buckets.
func groupTasksByStatus(tasks []domain.Task) map[string][]domain.Task {
	out := map[string][]domain.Task{
		"open":      {},
		"doing":     {},
		"done":      {},
		"cancelled": {},
	}
	for _, t := range tasks {
		bucket := t.Status
		if _, ok := out[bucket]; !ok {
			bucket = "open"
		}
		out[bucket] = append(out[bucket], t)
	}
	return out
}

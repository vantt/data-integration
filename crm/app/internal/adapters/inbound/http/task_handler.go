// Package http — Task HTTP handlers.
// Auth: DEFERRED — LAN-trust only (per plan).
package http

import (
	"context"
	"encoding/json"
	"log"
	"net/http"

	"github.com/go-chi/chi/v5"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// TaskQuerier is the read/list interface for tasks.
type TaskQuerier interface {
	GetTask(ctx context.Context, taskID string) (*domain.Task, error)
	ListTasks(ctx context.Context, assigneeUserID, status string) ([]domain.Task, error)
}

// TaskWriter covers task creation and mutation.
type TaskWriter interface {
	CreateTask(ctx context.Context, t *domain.Task) error
	AssignTask(ctx context.Context, taskID, assigneeUserID string) error
	TransitionStatus(ctx context.Context, taskID, newStatus string) error
}

// TaskGenerator triggers batch task generation from the action queue.
type TaskGenerator interface {
	GenerateTasksFromActionQueue(ctx context.Context) (int, error)
}

// TaskHandler wires task endpoints.
type TaskHandler struct {
	querier   TaskQuerier
	writer    TaskWriter
	generator TaskGenerator
}

// NewTaskHandler constructs the handler.
func NewTaskHandler(q TaskQuerier, w TaskWriter, g TaskGenerator) *TaskHandler {
	return &TaskHandler{querier: q, writer: w, generator: g}
}

// RegisterRoutes mounts task routes on the given chi router.
func (h *TaskHandler) RegisterRoutes(r chi.Router) {
	r.Get("/api/tasks", h.listTasks)
	r.Post("/api/tasks", h.createTask)
	r.Patch("/api/tasks/{id}", h.updateTask)
	r.Post("/api/tasks/generate-from-actions", h.generateFromActions)
}

// GET /api/tasks?assignee=<user_id>&status=<status>
func (h *TaskHandler) listTasks(w http.ResponseWriter, r *http.Request) {
	assignee := r.URL.Query().Get("assignee")
	status := r.URL.Query().Get("status")
	tasks, err := h.querier.ListTasks(r.Context(), assignee, status)
	if err != nil {
		log.Printf("task handler: list tasks: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to list tasks")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"tasks": tasks})
}

// POST /api/tasks
func (h *TaskHandler) createTask(w http.ResponseWriter, r *http.Request) {
	var body struct {
		PartyID        *string `json:"party_id"`
		Title          string  `json:"title"`
		Description    string  `json:"description"`
		DueAt          *string `json:"due_at"`
		Priority       int     `json:"priority"`
		AssigneeUserID *string `json:"assignee_user_id"`
		CreatedBy      *string `json:"created_by"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	t := &domain.Task{
		PartyID:        body.PartyID,
		Title:          body.Title,
		Description:    body.Description,
		DueAt:          body.DueAt,
		Priority:       body.Priority,
		AssigneeUserID: body.AssigneeUserID,
		CreatedBy:      body.CreatedBy,
	}
	if err := h.writer.CreateTask(r.Context(), t); err != nil {
		if domain.IsValidationError(err) {
			writeError(w, http.StatusBadRequest, err.Error())
		} else {
			log.Printf("task handler: create task: %v", err)
			writeError(w, http.StatusInternalServerError, "operation failed")
		}
		return
	}
	writeJSON(w, http.StatusCreated, t)
}

// PATCH /api/tasks/{id}   body: {"status":"doing"} or {"assignee_user_id":"..."}
func (h *TaskHandler) updateTask(w http.ResponseWriter, r *http.Request) {
	taskID := chi.URLParam(r, "id")

	var body struct {
		Status         *string `json:"status"`
		AssigneeUserID *string `json:"assignee_user_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if body.AssigneeUserID != nil {
		if err := h.writer.AssignTask(r.Context(), taskID, *body.AssigneeUserID); err != nil {
			if domain.IsValidationError(err) {
				writeError(w, http.StatusBadRequest, err.Error())
			} else {
				log.Printf("task handler: assign task %s: %v", taskID, err)
				writeError(w, http.StatusInternalServerError, "operation failed")
			}
			return
		}
	}
	if body.Status != nil {
		if err := h.writer.TransitionStatus(r.Context(), taskID, *body.Status); err != nil {
			if domain.IsValidationError(err) {
				writeError(w, http.StatusBadRequest, err.Error())
			} else {
				log.Printf("task handler: transition task %s → %s: %v", taskID, *body.Status, err)
				writeError(w, http.StatusInternalServerError, "operation failed")
			}
			return
		}
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "task_id": taskID})
}

// POST /api/tasks/generate-from-actions
func (h *TaskHandler) generateFromActions(w http.ResponseWriter, r *http.Request) {
	n, err := h.generator.GenerateTasksFromActionQueue(r.Context())
	if err != nil {
		log.Printf("task handler: generate from actions: %v", err)
		writeError(w, http.StatusInternalServerError, "failed to generate tasks")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"tasks_created": n})
}

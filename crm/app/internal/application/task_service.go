// Package application — TaskService: manual task CRUD + auto-generation from wh_action_queue.
// Pure domain + ports only; no adapter imports.
package application

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// TaskService handles task creation, assignment, status transitions,
// and auto-generation from the warehouse action queue.
type TaskService struct {
	taskRepo  ports.TaskRepository
	partyRepo ports.PartyRepository
	cacheRepo ports.CacheRepository
}

// NewTaskService constructs a TaskService.
func NewTaskService(
	taskRepo ports.TaskRepository,
	partyRepo ports.PartyRepository,
	cacheRepo ports.CacheRepository,
) *TaskService {
	return &TaskService{
		taskRepo:  taskRepo,
		partyRepo: partyRepo,
		cacheRepo: cacheRepo,
	}
}

// CreateTask validates and stores a manually-created task.
func (s *TaskService) CreateTask(ctx context.Context, t *domain.Task) error {
	if strings.TrimSpace(t.Title) == "" {
		return domain.NewValidationError("title is required")
	}
	now := utcNow()
	if t.TaskID == "" {
		t.TaskID = uuid.New().String()
	}
	if t.Source == "" {
		t.Source = "manual"
	}
	if t.Status == "" {
		t.Status = "open"
	}
	t.CreatedAt = now
	t.UpdatedAt = now
	return s.taskRepo.Insert(ctx, t)
}

// GetTask returns a task by ID, or nil if not found.
func (s *TaskService) GetTask(ctx context.Context, taskID string) (*domain.Task, error) {
	return s.taskRepo.GetByID(ctx, taskID)
}

// AssignTask assigns a task to a staff user.
func (s *TaskService) AssignTask(ctx context.Context, taskID, assigneeUserID string) error {
	t, err := s.taskRepo.GetByID(ctx, taskID)
	if err != nil {
		return fmt.Errorf("task service: assign: %w", err)
	}
	if t == nil {
		return fmt.Errorf("task service: task %q not found", taskID)
	}
	t.AssigneeUserID = &assigneeUserID
	// updated_at is owned by trg_task_touch trigger — no app-side stamp needed.
	return s.taskRepo.Update(ctx, t)
}

// TransitionStatus applies a status change, enforcing domain transition rules.
func (s *TaskService) TransitionStatus(ctx context.Context, taskID, newStatus string) error {
	if !domain.IsValidTaskStatus(newStatus) {
		return domain.NewValidationError(fmt.Sprintf("invalid task status %q", newStatus))
	}
	t, err := s.taskRepo.GetByID(ctx, taskID)
	if err != nil {
		return fmt.Errorf("task service: transition: %w", err)
	}
	if t == nil {
		return domain.NewValidationError(fmt.Sprintf("task %q not found", taskID))
	}
	if err := domain.CanTransitionTo(t.Status, newStatus); err != nil {
		// CanTransitionTo already returns a descriptive domain rule error.
		return domain.NewValidationError(err.Error())
	}
	t.Status = newStatus
	// updated_at is owned by trg_task_touch trigger — no app-side stamp needed.
	if newStatus == "done" || newStatus == "cancelled" {
		now := utcNow()
		t.CompletedAt = &now
	} else {
		t.CompletedAt = nil
	}
	return s.taskRepo.Update(ctx, t)
}

// ListTasks returns tasks filtered by optional assignee and/or status.
func (s *TaskService) ListTasks(ctx context.Context, assigneeUserID, status string) ([]domain.Task, error) {
	tasks, err := s.taskRepo.ListByAssigneeAndStatus(ctx, assigneeUserID, status)
	if err != nil {
		return nil, fmt.Errorf("task service: list tasks: %w", err)
	}
	if tasks == nil {
		tasks = []domain.Task{}
	}
	return tasks, nil
}

// GenerateTasksFromActionQueue reads all rows in cache.wh_action_queue and converts
// each unprocessed action into a crm_task (source='action_queue', source_ref=action_id).
//
// Idempotency: actions already converted are skipped (ExistsBySourceRef check).
// Party resolution: action.customer_key → sapo_customer identity → party_id.
//   If no party exists yet, party_id is left nil (task still created).
// Cache absent: returns (0, nil) gracefully.
//
// Returns the number of tasks created.
func (s *TaskService) GenerateTasksFromActionQueue(ctx context.Context) (int, error) {
	actions, err := s.cacheRepo.ListAllActionQueue(ctx)
	if err != nil {
		return 0, fmt.Errorf("task service: list action queue: %w", err)
	}
	if len(actions) == 0 {
		return 0, nil
	}

	created, skipped := 0, 0
	for _, action := range actions {
		n, err := s.processAction(ctx, action)
		if err != nil {
			log.Printf("task service: action %s: %v", action.ActionID, err)
			continue
		}
		created += n
		if n == 0 {
			skipped++
		}
	}
	log.Printf("task service: action_queue → %d tasks created, %d skipped (duplicate)", created, skipped)
	return created, nil
}

// processAction converts one ActionQueueItem into a task.
// Returns (1, nil) when created, (0, nil) when skipped as duplicate.
func (s *TaskService) processAction(ctx context.Context, action domain.ActionQueueItem) (int, error) {
	// Idempotency guard: skip if task already exists for this action_id.
	exists, err := s.taskRepo.ExistsBySourceRef(ctx, "action_queue", action.ActionID)
	if err != nil {
		return 0, fmt.Errorf("check duplicate: %w", err)
	}
	if exists {
		return 0, nil
	}

	// Resolve customer_key → party_id via sapo_customer identity.
	// customer_key in action_queue is the Sapo customer identifier string.
	var partyID *string
	if action.CustomerKey != "" {
		party, lookupErr := s.partyRepo.FindByIdentity(ctx, "sapo_customer", action.CustomerKey)
		if lookupErr != nil {
			log.Printf("task service: resolve party for customer_key=%s: %v", action.CustomerKey, lookupErr)
			// Non-fatal — create task without party link.
		} else if party != nil {
			partyID = &party.PartyID
		}
	}

	title := fmt.Sprintf("[%s] %s", action.ActionType, action.CustomerKey)
	if action.RationaleVI != "" {
		if len(action.RationaleVI) > 80 {
			title = fmt.Sprintf("[%s] %s", action.ActionType, action.RationaleVI[:80])
		} else {
			title = fmt.Sprintf("[%s] %s", action.ActionType, action.RationaleVI)
		}
	}

	sourceRef := action.ActionID
	now := utcNow()
	task := &domain.Task{
		TaskID:      uuid.New().String(),
		PartyID:     partyID,
		Title:       title,
		Description: action.RationaleVI,
		Priority:    action.Priority,
		Status:      "open",
		Source:      "action_queue",
		SourceRef:   &sourceRef,
		CreatedAt:   now,
		UpdatedAt:   now,
	}
	if err := s.taskRepo.Insert(ctx, task); err != nil {
		return 0, fmt.Errorf("insert task: %w", err)
	}
	return 1, nil
}

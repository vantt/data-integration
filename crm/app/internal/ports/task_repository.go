// Package ports — outbound port for Task persistence.
// Nothing here may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// TaskRepository persists and queries Task records.
type TaskRepository interface {
	// Insert stores a new task row.
	Insert(ctx context.Context, t *domain.Task) error

	// GetByID returns a task by primary key, or nil if not found.
	GetByID(ctx context.Context, taskID string) (*domain.Task, error)

	// Update persists mutable task fields (status, assignee, due_at, completed_at, updated_at).
	Update(ctx context.Context, t *domain.Task) error

	// ListByAssigneeAndStatus returns tasks filtered by assignee and/or status.
	// Empty string means "any" for that filter.
	ListByAssigneeAndStatus(ctx context.Context, assigneeUserID, status string) ([]domain.Task, error)

	// ExistsBySourceRef returns true when a task with the given source + source_ref already exists.
	// Used for idempotency in GenerateTasksFromActionQueue.
	ExistsBySourceRef(ctx context.Context, source, sourceRef string) (bool, error)
}

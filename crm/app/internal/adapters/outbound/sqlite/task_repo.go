// Package sqlite — TaskRepo: SQLite adapter implementing ports.TaskRepository.
package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite/sqlcgen"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// TaskRepo satisfies ports.TaskRepository.
type TaskRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewTaskRepo constructs a TaskRepo.
func NewTaskRepo(db *DB) ports.TaskRepository {
	return &TaskRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

// Insert stores a new task row.
func (r *TaskRepo) Insert(ctx context.Context, t *domain.Task) error {
	return r.q.InsertTask(ctx, sqlcgen.InsertTaskParams{
		TaskID:         t.TaskID,
		PartyID:        toNullStringPtr(t.PartyID),
		Title:          t.Title,
		Description:    toNullString(t.Description),
		DueAt:          toNullStringPtr(t.DueAt),
		Priority:       int64(t.Priority),
		Status:         t.Status,
		AssigneeUserID: toNullStringPtr(t.AssigneeUserID),
		Source:         t.Source,
		SourceRef:      toNullStringPtr(t.SourceRef),
		CreatedBy:      toNullStringPtr(t.CreatedBy),
		CreatedAt:      t.CreatedAt,
		UpdatedAt:      t.UpdatedAt,
		CompletedAt:    toNullStringPtr(t.CompletedAt),
	})
}

// GetByID returns a task by primary key, or nil if not found.
func (r *TaskRepo) GetByID(ctx context.Context, taskID string) (*domain.Task, error) {
	row, err := r.q.GetTaskByID(ctx, taskID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("task repo: get by id: %w", err)
	}
	t := taskFromRow(row)
	return &t, nil
}

// Update persists mutable task fields including title and description.
func (r *TaskRepo) Update(ctx context.Context, t *domain.Task) error {
	return r.q.UpdateTask(ctx, sqlcgen.UpdateTaskParams{
		Title:          t.Title,
		Description:    toNullString(t.Description),
		Status:         t.Status,
		AssigneeUserID: toNullStringPtr(t.AssigneeUserID),
		DueAt:          toNullStringPtr(t.DueAt),
		CompletedAt:    toNullStringPtr(t.CompletedAt),
		UpdatedAt:      t.UpdatedAt,
		TaskID:         t.TaskID,
	})
}

// ListByAssigneeAndStatus returns tasks filtered by assignee and/or status.
// Empty string means "any" for that filter.
// Uses composite-index query (assignee_user_id, status) when both are set.
func (r *TaskRepo) ListByAssigneeAndStatus(ctx context.Context, assigneeUserID, status string) ([]domain.Task, error) {
	var rows []sqlcgen.CrmTask
	var err error

	switch {
	case assigneeUserID != "" && status != "":
		// Use composite-index query to avoid fetching-all-then-filtering-in-Go.
		rows, err = r.q.ListTasksByAssigneeAndStatus(ctx, sqlcgen.ListTasksByAssigneeAndStatusParams{
			AssigneeUserID: toNullString(assigneeUserID),
			Status:         status,
		})
		if err != nil {
			return nil, fmt.Errorf("task repo: list by assignee+status: %w", err)
		}
	case assigneeUserID != "":
		rows, err = r.q.ListTasksByAssignee(ctx, toNullString(assigneeUserID))
		if err != nil {
			return nil, fmt.Errorf("task repo: list by assignee: %w", err)
		}
	case status != "":
		rows, err = r.q.ListTasksByStatus(ctx, status)
		if err != nil {
			return nil, fmt.Errorf("task repo: list by status: %w", err)
		}
	default:
		rows, err = r.q.ListAllTasks(ctx)
		if err != nil {
			return nil, fmt.Errorf("task repo: list all: %w", err)
		}
	}

	out := make([]domain.Task, 0, len(rows))
	for _, row := range rows {
		t := taskFromRow(row)
		out = append(out, t)
	}
	return out, nil
}

// ExistsBySourceRef returns true when a task with the given source + source_ref already exists.
func (r *TaskRepo) ExistsBySourceRef(ctx context.Context, source, sourceRef string) (bool, error) {
	count, err := r.q.ExistsTaskBySourceRef(ctx, sqlcgen.ExistsTaskBySourceRefParams{
		Source:    source,
		SourceRef: toNullString(sourceRef),
	})
	if err != nil {
		return false, fmt.Errorf("task repo: exists by source ref: %w", err)
	}
	return count > 0, nil
}

func taskFromRow(r sqlcgen.CrmTask) domain.Task {
	t := domain.Task{
		TaskID:    r.TaskID,
		Title:     r.Title,
		Priority:  int(r.Priority),
		Status:    r.Status,
		Source:    r.Source,
		CreatedAt: r.CreatedAt,
		UpdatedAt: r.UpdatedAt,
	}
	if r.PartyID.Valid {
		s := r.PartyID.String
		t.PartyID = &s
	}
	if r.Description.Valid {
		t.Description = r.Description.String
	}
	if r.DueAt.Valid {
		s := r.DueAt.String
		t.DueAt = &s
	}
	if r.AssigneeUserID.Valid {
		s := r.AssigneeUserID.String
		t.AssigneeUserID = &s
	}
	if r.SourceRef.Valid {
		s := r.SourceRef.String
		t.SourceRef = &s
	}
	if r.CreatedBy.Valid {
		s := r.CreatedBy.String
		t.CreatedBy = &s
	}
	if r.CompletedAt.Valid {
		s := r.CompletedAt.String
		t.CompletedAt = &s
	}
	return t
}

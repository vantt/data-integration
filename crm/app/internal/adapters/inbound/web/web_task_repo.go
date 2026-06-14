// Package web — WebTaskRepo: minimal task queries needed by the web adapter.
// Adds ListByParty (tasks for one customer 360 screen) via a raw SQL query
// on the shared *sql.DB without modifying ports.TaskRepository.
package web

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// WebTaskRepo satisfies TaskPartyQuerier.
type WebTaskRepo struct {
	db *sql.DB
}

// NewWebTaskRepo constructs a WebTaskRepo.
func NewWebTaskRepo(db *sql.DB) TaskPartyQuerier {
	return &WebTaskRepo{db: db}
}

// ListByParty returns all tasks for a party ordered by due_at ASC (nulls last), then priority DESC.
func (r *WebTaskRepo) ListByParty(ctx context.Context, partyID string) ([]domain.Task, error) {
	const q = `
		SELECT task_id, party_id, title, COALESCE(description,''),
		       due_at, priority, status,
		       COALESCE(assignee_user_id,''), source, COALESCE(source_ref,''),
		       COALESCE(created_by,''), created_at, updated_at, COALESCE(completed_at,'')
		FROM crm_task
		WHERE party_id = ?
		ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, due_at ASC, priority DESC`

	rows, err := r.db.QueryContext(ctx, q, partyID)
	if err != nil {
		return nil, fmt.Errorf("web task repo: list by party: %w", err)
	}
	defer rows.Close()

	var out []domain.Task
	for rows.Next() {
		var t domain.Task
		var partyIDVal, dueAt, assignee, sourceRef, createdBy, completedAt sql.NullString
		var priority int64
		if err := rows.Scan(
			&t.TaskID, &partyIDVal, &t.Title, &t.Description,
			&dueAt, &priority, &t.Status,
			&assignee, &t.Source, &sourceRef,
			&createdBy, &t.CreatedAt, &t.UpdatedAt, &completedAt,
		); err != nil {
			return nil, fmt.Errorf("web task repo: scan: %w", err)
		}
		t.Priority = int(priority)
		if partyIDVal.Valid && partyIDVal.String != "" {
			s := partyIDVal.String
			t.PartyID = &s
		}
		if dueAt.Valid && dueAt.String != "" {
			s := dueAt.String
			t.DueAt = &s
		}
		if assignee.Valid && assignee.String != "" {
			s := assignee.String
			t.AssigneeUserID = &s
		}
		if sourceRef.Valid && sourceRef.String != "" {
			s := sourceRef.String
			t.SourceRef = &s
		}
		if createdBy.Valid && createdBy.String != "" {
			s := createdBy.String
			t.CreatedBy = &s
		}
		if completedAt.Valid && completedAt.String != "" {
			s := completedAt.String
			t.CompletedAt = &s
		}
		out = append(out, t)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("web task repo: rows: %w", err)
	}
	if out == nil {
		out = []domain.Task{}
	}
	return out, nil
}

// Package ports — outbound port for Segment persistence.
// Nothing here may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// SegmentRepository persists and queries Segment and SegmentMember records.
type SegmentRepository interface {
	// Insert stores a new segment row.
	Insert(ctx context.Context, s *domain.Segment) error

	// GetByID returns a segment by primary key, or nil if not found.
	GetByID(ctx context.Context, segmentID string) (*domain.Segment, error)

	// Update persists mutable segment fields (name, description, is_dynamic, definition, owner_user_id).
	Update(ctx context.Context, s *domain.Segment) error

	// List returns all segments ordered by created_at DESC.
	List(ctx context.Context) ([]domain.Segment, error)

	// UpsertMember inserts or updates a segment member (idempotent on PK).
	UpsertMember(ctx context.Context, m *domain.SegmentMember) error

	// DeleteMember removes a party from a segment.
	DeleteMember(ctx context.Context, segmentID, partyID string) error

	// ListMembers returns all members of a segment.
	ListMembers(ctx context.Context, segmentID string) ([]domain.SegmentMember, error)

	// DeleteRuleMembers removes all rule-sourced members from a segment.
	// Called before re-evaluating a dynamic segment so stale members are purged.
	DeleteRuleMembers(ctx context.Context, segmentID string) error
}

// Package sqlite — SegmentRepo: SQLite adapter implementing ports.SegmentRepository.
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

// SegmentRepo satisfies ports.SegmentRepository.
type SegmentRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewSegmentRepo constructs a SegmentRepo.
func NewSegmentRepo(db *DB) ports.SegmentRepository {
	return &SegmentRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *SegmentRepo) Insert(ctx context.Context, s *domain.Segment) error {
	return r.q.InsertSegment(ctx, sqlcgen.InsertSegmentParams{
		SegmentID:   s.SegmentID,
		Name:        s.Name,
		Description: toNullString(s.Description),
		IsDynamic:   boolToInt64(s.IsDynamic),
		Definition:  toNullString(s.Definition),
		OwnerUserID: toNullStringPtr(s.OwnerUserID),
		CreatedAt:   s.CreatedAt,
		UpdatedAt:   s.UpdatedAt,
	})
}

func (r *SegmentRepo) GetByID(ctx context.Context, segmentID string) (*domain.Segment, error) {
	row, err := r.q.GetSegmentByID(ctx, segmentID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("segment repo: get by id: %w", err)
	}
	s := segmentFromRow(row)
	return &s, nil
}

func (r *SegmentRepo) Update(ctx context.Context, s *domain.Segment) error {
	return r.q.UpdateSegment(ctx, sqlcgen.UpdateSegmentParams{
		Name:        s.Name,
		Description: toNullString(s.Description),
		IsDynamic:   boolToInt64(s.IsDynamic),
		Definition:  toNullString(s.Definition),
		OwnerUserID: toNullStringPtr(s.OwnerUserID),
		UpdatedAt:   s.UpdatedAt,
		SegmentID:   s.SegmentID,
	})
}

func (r *SegmentRepo) List(ctx context.Context) ([]domain.Segment, error) {
	rows, err := r.q.ListSegments(ctx)
	if err != nil {
		return nil, fmt.Errorf("segment repo: list: %w", err)
	}
	out := make([]domain.Segment, 0, len(rows))
	for _, row := range rows {
		out = append(out, segmentFromRow(row))
	}
	return out, nil
}

func (r *SegmentRepo) UpsertMember(ctx context.Context, m *domain.SegmentMember) error {
	return r.q.UpsertSegmentMember(ctx, sqlcgen.UpsertSegmentMemberParams{
		SegmentID: m.SegmentID,
		PartyID:   m.PartyID,
		Source:    m.Source,
		AddedAt:   m.AddedAt,
	})
}

func (r *SegmentRepo) DeleteMember(ctx context.Context, segmentID, partyID string) error {
	return r.q.DeleteSegmentMember(ctx, sqlcgen.DeleteSegmentMemberParams{
		SegmentID: segmentID,
		PartyID:   partyID,
	})
}

func (r *SegmentRepo) ListMembers(ctx context.Context, segmentID string) ([]domain.SegmentMember, error) {
	rows, err := r.q.ListSegmentMembers(ctx, segmentID)
	if err != nil {
		return nil, fmt.Errorf("segment repo: list members: %w", err)
	}
	out := make([]domain.SegmentMember, 0, len(rows))
	for _, row := range rows {
		out = append(out, domain.SegmentMember{
			SegmentID: row.SegmentID,
			PartyID:   row.PartyID,
			Source:    row.Source,
			AddedAt:   row.AddedAt,
		})
	}
	return out, nil
}

func (r *SegmentRepo) DeleteRuleMembers(ctx context.Context, segmentID string) error {
	return r.q.DeleteRuleSegmentMembers(ctx, segmentID)
}

func segmentFromRow(r sqlcgen.CrmSegment) domain.Segment {
	s := domain.Segment{
		SegmentID: r.SegmentID,
		Name:      r.Name,
		IsDynamic: r.IsDynamic != 0,
		CreatedAt: r.CreatedAt,
		UpdatedAt: r.UpdatedAt,
	}
	if r.Description.Valid {
		s.Description = r.Description.String
	}
	if r.Definition.Valid {
		s.Definition = r.Definition.String
	}
	if r.OwnerUserID.Valid {
		v := r.OwnerUserID.String
		s.OwnerUserID = &v
	}
	return s
}

// boolToInt64 converts Go bool to SQLite INTEGER (1/0).
func boolToInt64(b bool) int64 {
	if b {
		return 1
	}
	return 0
}

// Package sqlite — ActivityRepo: SQLite adapter implementing ports.ActivityRepository.
package sqlite

import (
	"context"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite/sqlcgen"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// ActivityRepo satisfies ports.ActivityRepository.
type ActivityRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewActivityRepo constructs an ActivityRepo.
func NewActivityRepo(db *DB) ports.ActivityRepository {
	return &ActivityRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

// Insert stores a new activity row.
func (r *ActivityRepo) Insert(ctx context.Context, a *domain.Activity) error {
	return r.q.InsertActivity(ctx, sqlcgen.InsertActivityParams{
		ActivityID:       a.ActivityID,
		PartyID:          a.PartyID,
		ActivityType:     a.ActivityType,
		Direction:        toNullString(a.Direction),
		Channel:          toNullString(a.Channel),
		Subject:          toNullString(a.Subject),
		Body:             toNullString(a.Body),
		Outcome:          toNullString(a.Outcome),
		RelatedOrderCode: toNullString(a.RelatedOrderCode),
		StaffUserID:      toNullStringPtr(a.StaffUserID),
		OccurredAt:       a.OccurredAt,
		CreatedAt:        a.CreatedAt,
	})
}

// ListByParty returns activities for a party ordered by occurred_at DESC.
func (r *ActivityRepo) ListByParty(ctx context.Context, partyID string) ([]domain.Activity, error) {
	rows, err := r.q.ListActivitiesByParty(ctx, partyID)
	if err != nil {
		return nil, fmt.Errorf("activity repo: list by party: %w", err)
	}
	out := make([]domain.Activity, 0, len(rows))
	for _, row := range rows {
		out = append(out, activityFromRow(row))
	}
	return out, nil
}

func activityFromRow(r sqlcgen.CrmActivity) domain.Activity {
	var staffID *string
	if r.StaffUserID.Valid {
		s := r.StaffUserID.String
		staffID = &s
	}
	return domain.Activity{
		ActivityID:       r.ActivityID,
		PartyID:          r.PartyID,
		ActivityType:     r.ActivityType,
		Direction:        r.Direction.String,
		Channel:          r.Channel.String,
		Subject:          r.Subject.String,
		Body:             r.Body.String,
		Outcome:          r.Outcome.String,
		RelatedOrderCode: r.RelatedOrderCode.String,
		StaffUserID:      staffID,
		OccurredAt:       r.OccurredAt,
		CreatedAt:        r.CreatedAt,
	}
}

// toNullString and toNullStringPtr are defined in party_repo.go (same package).

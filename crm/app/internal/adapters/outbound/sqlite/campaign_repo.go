// Package sqlite — CampaignRepo: SQLite adapter implementing ports.CampaignRepository.
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

// CampaignRepo satisfies ports.CampaignRepository.
type CampaignRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewCampaignRepo constructs a CampaignRepo.
func NewCampaignRepo(db *DB) ports.CampaignRepository {
	return &CampaignRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *CampaignRepo) Insert(ctx context.Context, c *domain.Campaign) error {
	return r.q.InsertCampaign(ctx, sqlcgen.InsertCampaignParams{
		CampaignID:  c.CampaignID,
		Name:        c.Name,
		Objective:   c.Objective,
		Channel:     toNullString(c.Channel),
		SegmentID:   toNullStringPtr(c.SegmentID),
		Status:      c.Status,
		ScheduledAt: toNullStringPtr(c.ScheduledAt),
		CreatedBy:   toNullStringPtr(c.CreatedBy),
		CreatedAt:   c.CreatedAt,
		UpdatedAt:   c.UpdatedAt,
	})
}

func (r *CampaignRepo) GetByID(ctx context.Context, campaignID string) (*domain.Campaign, error) {
	row, err := r.q.GetCampaignByID(ctx, campaignID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("campaign repo: get by id: %w", err)
	}
	c := campaignFromRow(row)
	return &c, nil
}

func (r *CampaignRepo) Update(ctx context.Context, c *domain.Campaign) error {
	return r.q.UpdateCampaign(ctx, sqlcgen.UpdateCampaignParams{
		Name:        c.Name,
		Objective:   c.Objective,
		Channel:     toNullString(c.Channel),
		SegmentID:   toNullStringPtr(c.SegmentID),
		Status:      c.Status,
		ScheduledAt: toNullStringPtr(c.ScheduledAt),
		UpdatedAt:   c.UpdatedAt,
		CampaignID:  c.CampaignID,
	})
}

func (r *CampaignRepo) List(ctx context.Context) ([]domain.Campaign, error) {
	rows, err := r.q.ListCampaigns(ctx)
	if err != nil {
		return nil, fmt.Errorf("campaign repo: list: %w", err)
	}
	out := make([]domain.Campaign, 0, len(rows))
	for _, row := range rows {
		out = append(out, campaignFromRow(row))
	}
	return out, nil
}

func (r *CampaignRepo) UpsertTarget(ctx context.Context, t *domain.CampaignTarget) error {
	return r.q.UpsertCampaignTarget(ctx, sqlcgen.UpsertCampaignTargetParams{
		CampaignID:          t.CampaignID,
		PartyID:             t.PartyID,
		Status:              t.Status,
		AssignedUserID:      toNullStringPtr(t.AssignedUserID),
		LastTouchAt:         toNullStringPtr(t.LastTouchAt),
		ConvertedOrderCode:  toNullStringPtr(t.ConvertedOrderCode),
		ConvertedRevenueVnd: toNullInt64Ptr(t.ConvertedRevenueVND),
		ConvertedAt:         toNullStringPtr(t.ConvertedAt),
	})
}

func (r *CampaignRepo) UpdateTarget(ctx context.Context, t *domain.CampaignTarget) error {
	return r.q.UpdateCampaignTarget(ctx, sqlcgen.UpdateCampaignTargetParams{
		Status:              t.Status,
		AssignedUserID:      toNullStringPtr(t.AssignedUserID),
		LastTouchAt:         toNullStringPtr(t.LastTouchAt),
		ConvertedOrderCode:  toNullStringPtr(t.ConvertedOrderCode),
		ConvertedRevenueVnd: toNullInt64Ptr(t.ConvertedRevenueVND),
		ConvertedAt:         toNullStringPtr(t.ConvertedAt),
		CampaignID:          t.CampaignID,
		PartyID:             t.PartyID,
	})
}

func (r *CampaignRepo) GetTarget(ctx context.Context, campaignID, partyID string) (*domain.CampaignTarget, error) {
	row, err := r.q.GetCampaignTarget(ctx, sqlcgen.GetCampaignTargetParams{
		CampaignID: campaignID,
		PartyID:    partyID,
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("campaign repo: get target: %w", err)
	}
	t := targetFromRow(row)
	return &t, nil
}

func (r *CampaignRepo) ListTargets(ctx context.Context, campaignID string) ([]domain.CampaignTarget, error) {
	rows, err := r.q.ListCampaignTargets(ctx, campaignID)
	if err != nil {
		return nil, fmt.Errorf("campaign repo: list targets: %w", err)
	}
	return targetsFromRows(rows), nil
}

func (r *CampaignRepo) ListTargetsByCampaignAndStatus(ctx context.Context, campaignID, status string) ([]domain.CampaignTarget, error) {
	if status == "" {
		return r.ListTargets(ctx, campaignID)
	}
	rows, err := r.q.ListCampaignTargetsByStatus(ctx, sqlcgen.ListCampaignTargetsByStatusParams{
		CampaignID: campaignID,
		Status:     status,
	})
	if err != nil {
		return nil, fmt.Errorf("campaign repo: list targets by status: %w", err)
	}
	return targetsFromRows(rows), nil
}

// ─── mapping helpers ──────────────────────────────────────────────────────────

func campaignFromRow(r sqlcgen.CrmCampaign) domain.Campaign {
	c := domain.Campaign{
		CampaignID: r.CampaignID,
		Name:       r.Name,
		Objective:  r.Objective,
		Status:     r.Status,
		CreatedAt:  r.CreatedAt,
		UpdatedAt:  r.UpdatedAt,
	}
	if r.Channel.Valid {
		c.Channel = r.Channel.String
	}
	if r.SegmentID.Valid {
		v := r.SegmentID.String
		c.SegmentID = &v
	}
	if r.ScheduledAt.Valid {
		v := r.ScheduledAt.String
		c.ScheduledAt = &v
	}
	if r.CreatedBy.Valid {
		v := r.CreatedBy.String
		c.CreatedBy = &v
	}
	return c
}

func targetFromRow(r sqlcgen.CrmCampaignTarget) domain.CampaignTarget {
	t := domain.CampaignTarget{
		CampaignID: r.CampaignID,
		PartyID:    r.PartyID,
		Status:     r.Status,
	}
	if r.AssignedUserID.Valid {
		v := r.AssignedUserID.String
		t.AssignedUserID = &v
	}
	if r.LastTouchAt.Valid {
		v := r.LastTouchAt.String
		t.LastTouchAt = &v
	}
	if r.ConvertedOrderCode.Valid {
		v := r.ConvertedOrderCode.String
		t.ConvertedOrderCode = &v
	}
	if r.ConvertedRevenueVnd.Valid {
		v := r.ConvertedRevenueVnd.Int64
		t.ConvertedRevenueVND = &v
	}
	if r.ConvertedAt.Valid {
		v := r.ConvertedAt.String
		t.ConvertedAt = &v
	}
	return t
}

func targetsFromRows(rows []sqlcgen.CrmCampaignTarget) []domain.CampaignTarget {
	out := make([]domain.CampaignTarget, 0, len(rows))
	for _, row := range rows {
		out = append(out, targetFromRow(row))
	}
	return out
}

// toNullInt64Ptr converts *int64 to sql.NullInt64.
func toNullInt64Ptr(v *int64) sql.NullInt64 {
	if v == nil {
		return sql.NullInt64{}
	}
	return sql.NullInt64{Int64: *v, Valid: true}
}

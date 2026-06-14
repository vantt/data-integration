// Package ports — outbound port for Campaign persistence.
// Nothing here may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// CampaignRepository persists and queries Campaign and CampaignTarget records.
type CampaignRepository interface {
	// Insert stores a new campaign row.
	Insert(ctx context.Context, c *domain.Campaign) error

	// GetByID returns a campaign by primary key, or nil if not found.
	GetByID(ctx context.Context, campaignID string) (*domain.Campaign, error)

	// Update persists mutable campaign fields (name, objective, channel, segment_id, status, scheduled_at).
	Update(ctx context.Context, c *domain.Campaign) error

	// List returns all campaigns ordered by created_at DESC.
	List(ctx context.Context) ([]domain.Campaign, error)

	// UpsertTarget inserts or ignores a campaign target (idempotent on PK).
	UpsertTarget(ctx context.Context, t *domain.CampaignTarget) error

	// UpdateTarget persists mutable target fields (status, assigned_user_id, last_touch_at,
	// converted_order_code, converted_revenue_vnd, converted_at).
	UpdateTarget(ctx context.Context, t *domain.CampaignTarget) error

	// GetTarget returns a single target row, or nil if not found.
	GetTarget(ctx context.Context, campaignID, partyID string) (*domain.CampaignTarget, error)

	// ListTargets returns all targets for a campaign.
	ListTargets(ctx context.Context, campaignID string) ([]domain.CampaignTarget, error)

	// ListTargetsByCampaignAndStatus returns targets filtered by status (empty = all).
	ListTargetsByCampaignAndStatus(ctx context.Context, campaignID, status string) ([]domain.CampaignTarget, error)
}

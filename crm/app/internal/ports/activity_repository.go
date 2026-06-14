// Package ports — outbound port for Activity persistence.
// Nothing here may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ActivityRepository persists and queries Activity records.
type ActivityRepository interface {
	// Insert stores a new activity row.
	Insert(ctx context.Context, a *domain.Activity) error

	// ListByParty returns activities for a party ordered by occurred_at DESC (newest first).
	ListByParty(ctx context.Context, partyID string) ([]domain.Activity, error)
}

// Package ports — outbound port for the warehouse cache (cache.db read-only).
// Nothing here may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// CacheRepository is the outbound port for reading from cache.db (ATTACHed read-only).
// All methods MUST gracefully handle the case where the wh_* tables do not yet exist
// (cache.db is empty before the first Python sync run) by returning nil/empty with no error.
type CacheRepository interface {
	// GetCustomerInsight returns the cached insight, latest actions, and recent orders
	// for the given Sapo customer_id.
	// Returns (nil, nil) when no data exists or the cache tables are absent.
	GetCustomerInsight(ctx context.Context, customerID int64) (*domain.CacheInsight, error)

	// ListPartySeed returns all rows from wh_party_seed that the seed consumer
	// has not yet processed.  Returns an empty slice when the table is absent.
	ListPartySeed(ctx context.Context) ([]domain.PartySeed, error)

	// ListAllActionQueue returns all rows from wh_action_queue regardless of customer.
	// Used by GenerateTasksFromActionQueue to batch-convert actions to tasks.
	// Returns an empty slice (no error) when the table is absent.
	ListAllActionQueue(ctx context.Context) ([]domain.ActionQueueItem, error)
}

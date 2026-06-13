// Package ports defines inbound and outbound interfaces for the CRM hexagonal architecture.
// Nothing in this package may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// AppUserRepository is the outbound port for persisting and querying CRM app users.
type AppUserRepository interface {
	GetByEmail(ctx context.Context, email string) (*domain.AppUser, error)
	ListActive(ctx context.Context) ([]domain.AppUser, error)
}

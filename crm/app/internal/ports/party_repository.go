// Package ports defines inbound and outbound interfaces for the CRM hexagonal architecture.
// Nothing in this package may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// PartyRepository is the outbound port for persisting and querying Party golden records
// and their associated identities.
type PartyRepository interface {
	// FindByIdentity returns the party that owns the given identity, or nil if not found.
	FindByIdentity(ctx context.Context, identityType, identityValue string) (*domain.Party, error)

	// Create inserts a new party row.
	Create(ctx context.Context, p *domain.Party) error

	// GetByID returns a party by primary key, or nil if not found.
	GetByID(ctx context.Context, partyID string) (*domain.Party, error)

	// Update persists changes to mutable party fields (display_name, primary_phone,
	// primary_email, status, is_merged, merged_into).
	Update(ctx context.Context, p *domain.Party) error

	// ListByPhone returns all non-merged parties with a matching normalised primary_phone.
	ListByPhone(ctx context.Context, phone string) ([]domain.Party, error)

	// ListByEmail returns all non-merged parties with a matching normalised primary_email.
	ListByEmail(ctx context.Context, email string) ([]domain.Party, error)

	// SearchByName runs an FTS5 MATCH on crm_party_fts and returns matching party IDs.
	// The caller is responsible for post-filtering (e.g. phone-prefix narrowing).
	SearchByName(ctx context.Context, query string) ([]string, error)

	// UpsertIdentity inserts or ignores a party_identity row.
	// The UNIQUE(identity_type, identity_value) constraint is the dedup guarantee.
	UpsertIdentity(ctx context.Context, id *domain.PartyIdentity) error

	// ListIdentities returns all identity rows for a given party.
	ListIdentities(ctx context.Context, partyID string) ([]domain.PartyIdentity, error)

	// CreateWithIdentities inserts a party and all supplied identities in a single
	// atomic transaction. Prevents an orphan party row when identity attachment fails mid-way.
	CreateWithIdentities(ctx context.Context, p *domain.Party, identities []*domain.PartyIdentity) error

	// UpdateContactQuality updates the mutable contact_quality field on an identity row.
	// Valid values: masked | unverified | verified.
	UpdateContactQuality(ctx context.Context, identityID, quality string) error
}

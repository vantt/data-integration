// Package ports — outbound repository interfaces for Customer 360.
// Nothing here may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// ProfileRepository is the outbound port for crm_customer_profile persistence.
type ProfileRepository interface {
	// GetProfile returns the enrichment profile for partyID, or nil if none exists yet.
	GetProfile(ctx context.Context, partyID string) (*domain.CustomerProfile, error)

	// UpsertProfile inserts or replaces the profile for a party (ON CONFLICT DO UPDATE).
	UpsertProfile(ctx context.Context, p *domain.CustomerProfile) error

	// UpdateCustomJSON replaces the entire custom JSON column for a party profile.
	// Caller must merge the existing JSON with new values before calling this.
	UpdateCustomJSON(ctx context.Context, partyID, customJSON string) error

	// GetParty360 queries the crm_party_360 view for a single party.
	// Returns nil when the party does not exist (or is merged).
	GetParty360(ctx context.Context, partyID string) (*domain.Party360, error)
}

// CustomFieldRepository is the outbound port for crm_custom_field_def CRUD.
type CustomFieldRepository interface {
	// ListActiveDefs returns all active custom field definitions for entityType
	// (e.g. "party"), ordered by sort_order.
	ListActiveDefs(ctx context.Context, entityType string) ([]domain.CustomFieldDef, error)

	// ListAllDefs returns all defs (active + inactive) for entityType.
	ListAllDefs(ctx context.Context, entityType string) ([]domain.CustomFieldDef, error)

	// GetDef returns a single definition by field_id, or nil if not found.
	GetDef(ctx context.Context, fieldID string) (*domain.CustomFieldDef, error)

	// CreateDef inserts a new custom field definition.
	CreateDef(ctx context.Context, d *domain.CustomFieldDef) error

	// UpdateDef persists changes to label, options, is_required, is_active, sort_order.
	UpdateDef(ctx context.Context, d *domain.CustomFieldDef) error
}

// TagRepository is the outbound port for crm_tag + crm_party_tag operations.
type TagRepository interface {
	// ListTags returns all tags, optionally filtered by category (empty = all).
	ListTags(ctx context.Context, category string) ([]domain.Tag, error)

	// GetTag returns a single tag by tag_id, or nil if not found.
	GetTag(ctx context.Context, tagID string) (*domain.Tag, error)

	// CreateTag inserts a new tag (UNIQUE on category+name enforced at DB level).
	CreateTag(ctx context.Context, t *domain.Tag) error

	// AttachTag creates a crm_party_tag row (INSERT OR IGNORE — idempotent on duplicate).
	AttachTag(ctx context.Context, pt *domain.PartyTag) error

	// DetachTag removes a crm_party_tag row.
	DetachTag(ctx context.Context, partyID, tagID string) error

	// ListPartyTags returns all tags currently attached to partyID.
	ListPartyTags(ctx context.Context, partyID string) ([]domain.Tag, error)
}

// NoteRepository is the outbound port for crm_note persistence.
type NoteRepository interface {
	// AddNote inserts a new note for a party.
	AddNote(ctx context.Context, n *domain.Note) error

	// ListNotes returns notes for partyID ordered by created_at DESC.
	ListNotes(ctx context.Context, partyID string) ([]domain.Note, error)
}

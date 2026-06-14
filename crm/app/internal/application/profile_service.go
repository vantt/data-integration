// Package application — ProfileService: Customer 360 business logic.
// Depends only on ports (interfaces) and domain — no adapter imports.
package application

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// ProfileService orchestrates profile enrichment, custom-field validation,
// tag management, and note operations for a party.
type ProfileService struct {
	profiles     ports.ProfileRepository
	customFields ports.CustomFieldRepository
	tags         ports.TagRepository
	notes        ports.NoteRepository
}

// NewProfileService constructs a ProfileService.
func NewProfileService(
	profiles ports.ProfileRepository,
	customFields ports.CustomFieldRepository,
	tags ports.TagRepository,
	notes ports.NoteRepository,
) *ProfileService {
	return &ProfileService{
		profiles:     profiles,
		customFields: customFields,
		tags:         tags,
		notes:        notes,
	}
}

// GetProfile returns the enrichment profile for a party (nil when none created yet).
func (s *ProfileService) GetProfile(ctx context.Context, partyID string) (*domain.CustomerProfile, error) {
	p, err := s.profiles.GetProfile(ctx, partyID)
	if err != nil {
		return nil, fmt.Errorf("profile service: get profile: %w", err)
	}
	return p, nil
}

// UpsertProfile creates or replaces the profile for a party.
// custom JSON field is preserved from the existing row when not supplied in p.Custom.
func (s *ProfileService) UpsertProfile(ctx context.Context, p *domain.CustomerProfile) error {
	if p.PartyID == "" {
		return fmt.Errorf("profile service: upsert: party_id required")
	}
	if p.Custom == "" {
		p.Custom = "{}"
	}
	if p.CreatedAt == "" {
		p.CreatedAt = utcNow()
	}
	p.UpdatedAt = utcNow()
	if err := s.profiles.UpsertProfile(ctx, p); err != nil {
		return fmt.Errorf("profile service: upsert profile: %w", err)
	}
	return nil
}

// UpdateCustom merges newValues into the existing custom JSON for partyID.
//
// Validation flow:
//  1. Load active crm_custom_field_def rows for entity_type='party'.
//  2. Load existing custom JSON from profile (or start with {}).
//  3. Merge: existing keys updated/added by newValues; omitted keys untouched.
//  4. Validate the FULL merged map so required-field checks apply to the complete state,
//     not just the incoming delta.
//  5. Persist the merged JSON.
func (s *ProfileService) UpdateCustom(ctx context.Context, partyID string, newValues map[string]string) error {
	// 1. Load active field definitions.
	defs, err := s.customFields.ListActiveDefs(ctx, "party")
	if err != nil {
		return fmt.Errorf("profile service: load custom field defs: %w", err)
	}

	// 2. Load existing custom JSON.
	existing := map[string]any{}
	profile, err := s.profiles.GetProfile(ctx, partyID)
	if err != nil {
		return fmt.Errorf("profile service: get profile for custom update: %w", err)
	}
	if profile != nil && profile.Custom != "" && profile.Custom != "{}" {
		if err := json.Unmarshal([]byte(profile.Custom), &existing); err != nil {
			// Corrupted stored value — reset gracefully.
			existing = map[string]any{}
		}
	}

	// 3. Merge newValues on top of existing.
	for k, v := range newValues {
		existing[k] = v
	}

	// 4. Validate the full merged map (type checks on new keys; required checks on complete state).
	// Convert merged map to map[string]string for ValidateCustomMap (values stored as strings).
	mergedStr := make(map[string]string, len(existing))
	for k, v := range existing {
		switch sv := v.(type) {
		case string:
			mergedStr[k] = sv
		default:
			mergedStr[k] = fmt.Sprintf("%v", sv)
		}
	}
	errs := domain.ValidateCustomMap(defs, mergedStr)
	if len(errs) > 0 {
		msgs := make([]string, len(errs))
		for i, e := range errs {
			msgs[i] = e.Error()
		}
		return fmt.Errorf("profile service: custom field validation failed: %s", strings.Join(msgs, "; "))
	}

	// 5. Persist merged JSON.
	merged, err := json.Marshal(existing)
	if err != nil {
		return fmt.Errorf("profile service: marshal custom json: %w", err)
	}

	// If no profile row yet, create a minimal one to hold the custom field.
	if profile == nil {
		p := &domain.CustomerProfile{
			PartyID:        partyID,
			Custom:         string(merged),
			ConsentContact: true,
			CreatedAt:      utcNow(),
			UpdatedAt:      utcNow(),
		}
		if err := s.profiles.UpsertProfile(ctx, p); err != nil {
			return fmt.Errorf("profile service: create profile for custom update: %w", err)
		}
		return nil
	}

	if err := s.profiles.UpdateCustomJSON(ctx, partyID, string(merged)); err != nil {
		return fmt.Errorf("profile service: persist custom json: %w", err)
	}
	return nil
}

// SetConsent updates the consent_contact flag for a party profile.
func (s *ProfileService) SetConsent(ctx context.Context, partyID string, consent bool) error {
	profile, err := s.profiles.GetProfile(ctx, partyID)
	if err != nil {
		return fmt.Errorf("profile service: get profile for consent: %w", err)
	}
	if profile == nil {
		profile = &domain.CustomerProfile{
			PartyID:        partyID,
			Custom:         "{}",
			ConsentContact: consent,
			CreatedAt:      utcNow(),
			UpdatedAt:      utcNow(),
		}
	} else {
		profile.ConsentContact = consent
	}
	return s.profiles.UpsertProfile(ctx, profile)
}

// GetParty360 returns the aggregated Party360 view for one party.
func (s *ProfileService) GetParty360(ctx context.Context, partyID string) (*domain.Party360, error) {
	v, err := s.profiles.GetParty360(ctx, partyID)
	if err != nil {
		return nil, fmt.Errorf("profile service: get party360: %w", err)
	}
	return v, nil
}

// --- Tag operations ---

// AttachTag attaches a tag to a party (idempotent — duplicate attach is a no-op).
func (s *ProfileService) AttachTag(ctx context.Context, partyID, tagID string, taggedBy *string) error {
	pt := &domain.PartyTag{
		PartyID:  partyID,
		TagID:    tagID,
		TaggedBy: taggedBy,
		TaggedAt: utcNow(),
	}
	if err := s.tags.AttachTag(ctx, pt); err != nil {
		return fmt.Errorf("profile service: attach tag: %w", err)
	}
	return nil
}

// DetachTag removes a tag from a party.
func (s *ProfileService) DetachTag(ctx context.Context, partyID, tagID string) error {
	if err := s.tags.DetachTag(ctx, partyID, tagID); err != nil {
		return fmt.Errorf("profile service: detach tag: %w", err)
	}
	return nil
}

// ListPartyTags returns all tags attached to partyID.
func (s *ProfileService) ListPartyTags(ctx context.Context, partyID string) ([]domain.Tag, error) {
	return s.tags.ListPartyTags(ctx, partyID)
}

// --- Note operations ---

// AddNote creates a new note for partyID.
func (s *ProfileService) AddNote(ctx context.Context, partyID, body string, authorUserID *string) (*domain.Note, error) {
	if strings.TrimSpace(body) == "" {
		return nil, fmt.Errorf("profile service: note body must not be empty")
	}
	n := &domain.Note{
		NoteID:       uuid.New().String(),
		PartyID:      partyID,
		Body:         body,
		AuthorUserID: authorUserID,
		CreatedAt:    utcNow(),
	}
	if err := s.notes.AddNote(ctx, n); err != nil {
		return nil, fmt.Errorf("profile service: add note: %w", err)
	}
	return n, nil
}

// ListNotes returns notes for partyID ordered by created_at DESC.
func (s *ProfileService) ListNotes(ctx context.Context, partyID string) ([]domain.Note, error) {
	return s.notes.ListNotes(ctx, partyID)
}

// --- Custom field def admin ---

// ListCustomFieldDefs returns active definitions for entityType.
func (s *ProfileService) ListCustomFieldDefs(ctx context.Context, entityType string) ([]domain.CustomFieldDef, error) {
	return s.customFields.ListActiveDefs(ctx, entityType)
}

// CreateCustomFieldDef inserts a new custom field definition.
func (s *ProfileService) CreateCustomFieldDef(ctx context.Context, d *domain.CustomFieldDef) error {
	if d.FieldID == "" {
		d.FieldID = uuid.New().String()
	}
	if d.EntityType == "" {
		d.EntityType = "party"
	}
	if err := s.customFields.CreateDef(ctx, d); err != nil {
		return fmt.Errorf("profile service: create custom field def: %w", err)
	}
	return nil
}

// UpdateCustomFieldDef persists changes to an existing definition.
func (s *ProfileService) UpdateCustomFieldDef(ctx context.Context, d *domain.CustomFieldDef) error {
	if err := s.customFields.UpdateDef(ctx, d); err != nil {
		return fmt.Errorf("profile service: update custom field def: %w", err)
	}
	return nil
}

// GetCustomFieldDef returns a single definition by field_id, or nil if not found.
func (s *ProfileService) GetCustomFieldDef(ctx context.Context, fieldID string) (*domain.CustomFieldDef, error) {
	return s.customFields.GetDef(ctx, fieldID)
}

// ListTags returns all tags optionally filtered by category (empty = all).
func (s *ProfileService) ListTags(ctx context.Context, category string) ([]domain.Tag, error) {
	return s.tags.ListTags(ctx, category)
}

// CreateTag inserts a new tag.
func (s *ProfileService) CreateTag(ctx context.Context, t *domain.Tag) error {
	if t.TagID == "" {
		t.TagID = uuid.New().String()
	}
	if err := s.tags.CreateTag(ctx, t); err != nil {
		return fmt.Errorf("profile service: create tag: %w", err)
	}
	return nil
}

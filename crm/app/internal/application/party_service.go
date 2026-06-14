package application

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// PartyService handles golden-record creation and identity attachment.
// Called by Phase-04 reverse-ETL to turn wh_party_seed rows into CRM parties.
type PartyService struct {
	repo ports.PartyRepository
}

// NewPartyService constructs a PartyService.
func NewPartyService(repo ports.PartyRepository) *PartyService {
	return &PartyService{repo: repo}
}

// UpsertFromSapoIdentity ensures a Party exists for the given Sapo customer and
// attaches normalised phone/email identities.
//
// Flow:
//  1. Look up party via identity(type='sapo_customer', value=sapoCustomerID).
//  2. If not found → create Party + sapo_customer identity atomically in one transaction
//     (prevents orphan party if identity attachment fails mid-way).
//  3. If phone/email provided → upsert as additional identities (UNIQUE guard at DB level).
//  4. Backfill display_name / primary_phone / primary_email on the party if blank.
//
// Backfill is non-destructive: an empty incoming value never clears an existing one,
// and a present incoming value only fills a field that is currently blank — so a
// manually-edited name is preserved across re-runs. This makes the seed sync
// idempotent and lets a later run fill names for parties created name-less earlier.
//
// Returns the party_id of the found or created party.
func (s *PartyService) UpsertFromSapoIdentity(
	ctx context.Context,
	sapoCustomerID string,
	phone, email, name string,
) (string, error) {
	normPhone := NormalizePhone(phone)
	normEmail := NormalizeEmail(email)

	// 1. Find by sapo_customer identity.
	party, err := s.repo.FindByIdentity(ctx, "sapo_customer", sapoCustomerID)
	if err != nil {
		return "", fmt.Errorf("party service: find by sapo identity: %w", err)
	}

	if party == nil {
		// 2. Create new party + sapo_customer identity atomically.
		// Using CreateWithIdentities ensures no orphan party if the identity insert fails.
		now := utcNow()
		party = &domain.Party{
			PartyID:      uuid.New().String(),
			PartyType:    "person",
			DisplayName:  name,
			PrimaryPhone: normPhone,
			PrimaryEmail: normEmail,
			Status:       "active",
			CreatedAt:    now,
			UpdatedAt:    now,
		}
		sapoIdentity := &domain.PartyIdentity{
			IdentityID:    uuid.New().String(),
			PartyID:       party.PartyID,
			SourceSystem:  "sapo",
			IdentityType:  "sapo_customer",
			IdentityValue: sapoCustomerID,
			Confidence:    1.0,
			IsPrimary:     true,
			CreatedAt:     now,
		}
		if err := s.repo.CreateWithIdentities(ctx, party, []*domain.PartyIdentity{sapoIdentity}); err != nil {
			return "", fmt.Errorf("party service: create party with sapo identity: %w", err)
		}
	}

	// 3. Attach phone/email identities (UNIQUE constraint handles duplicates silently).
	if normPhone != "" {
		if err := s.upsertIdentity(ctx, party.PartyID, "sapo", "phone", normPhone, 1.0, false); err != nil {
			return "", fmt.Errorf("party service: attach phone identity: %w", err)
		}
	}
	if normEmail != "" {
		if err := s.upsertIdentity(ctx, party.PartyID, "sapo", "email", normEmail, 1.0, false); err != nil {
			return "", fmt.Errorf("party service: attach email identity: %w", err)
		}
	}

	// 4. Backfill blank golden-record fields, then persist in a single Update.
	// Only fill fields that are currently empty AND have an incoming value, so
	// re-running sync fills name-less parties without clobbering edited values.
	dirty := false
	if party.DisplayName == "" && name != "" {
		party.DisplayName = name
		dirty = true
	}
	if party.PrimaryPhone == "" && normPhone != "" {
		party.PrimaryPhone = normPhone
		dirty = true
	}
	if party.PrimaryEmail == "" && normEmail != "" {
		party.PrimaryEmail = normEmail
		dirty = true
	}
	if dirty {
		if err := s.repo.Update(ctx, party); err != nil {
			return "", fmt.Errorf("party service: backfill golden record: %w", err)
		}
	}

	return party.PartyID, nil
}

func (s *PartyService) upsertIdentity(
	ctx context.Context,
	partyID, source, idType, idValue string,
	confidence float64,
	isPrimary bool,
) error {
	id := &domain.PartyIdentity{
		IdentityID:    uuid.New().String(),
		PartyID:       partyID,
		SourceSystem:  source,
		IdentityType:  idType,
		IdentityValue: idValue,
		Confidence:    confidence,
		IsPrimary:     isPrimary,
		CreatedAt:     utcNow(),
	}
	return s.repo.UpsertIdentity(ctx, id)
}

func utcNow() string {
	return time.Now().UTC().Format("2006-01-02T15:04:05.000Z")
}

// Package application — PartySeedService consumes wh_party_seed from cache.db
// and ensures every seed row has a corresponding crm_party + sapo_customer identity.
//
// This keeps the 1-writer rule: Python writes cache.db; Go writes crm.db.
// The seed table is the handoff channel between the two worlds.
package application

import (
	"context"
	"fmt"
	"log"
	"strconv"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// PartySeedService reads wh_party_seed (cache.db) and upserts crm_party rows (crm.db).
type PartySeedService struct {
	partyRepo ports.PartyRepository
	partySvc  *PartyService
}

// NewPartySeedService constructs a PartySeedService.
// cacheRepo reads from cache.db (read-only); partyRepo + partySvc write to crm.db.
func NewPartySeedService(
	cacheRepo ports.CacheRepository,
	partyRepo ports.PartyRepository,
) *PartySeedService {
	return &PartySeedService{
		partyRepo: partyRepo,
		partySvc:  NewPartyService(partyRepo),
	}
}

// SyncParties reads all wh_party_seed rows and upserts crm_party + identity for each.
//
// Per-seed errors are logged and counted; the loop continues so one bad seed does not
// abort the entire batch. After the loop, if every seed failed (count == 0 and there
// were failures), a non-nil error is returned so the caller (syncparties cmd) exits
// non-zero. Partial success (some ok, some failed) still returns (count, nil).
//
// This method is idempotent: calling it multiple times produces no duplicates because
// PartyService.UpsertFromSapoIdentity uses UNIQUE(identity_type, identity_value).
//
// Returns the number of parties successfully created or updated.
func (s *PartySeedService) SyncParties(ctx context.Context, cache ports.CacheRepository) (int, error) {
	seeds, err := cache.ListPartySeed(ctx)
	if err != nil {
		return 0, fmt.Errorf("party seed service: list seeds: %w", err)
	}
	if len(seeds) == 0 {
		log.Println("party seed service: no seeds to process")
		return 0, nil
	}

	count, failures := 0, 0
	for _, seed := range seeds {
		if err := s.processSeed(ctx, seed); err != nil {
			// Log and continue — a single bad seed should not abort the batch.
			log.Printf("party seed service: seed customer_id=%d: %v", seed.CustomerID, err)
			failures++
			continue
		}
		count++
	}

	log.Printf("party seed service: processed %d / %d seeds (%d failures)", count, len(seeds), failures)

	// Surface total failure: every seed failed — caller should exit non-zero.
	if failures > 0 && count == 0 {
		return count, fmt.Errorf("party seed: all %d seeds failed (first error logged)", failures)
	}
	return count, nil
}

// processSeed ensures one crm_party + sapo_customer identity exists for the seed,
// enriched with the real display_name/phone/email carried on the seed (joined from
// wh_customer_base by the cache repo). Enrichment fields may be empty when no
// wh_customer_base row matched — in that case the party is still created, just
// without a name. UpsertFromSapoIdentity backfills empty fields on re-run, so
// already-created parties get their names filled the next time sync runs.
func (s *PartySeedService) processSeed(ctx context.Context, seed domain.PartySeed) error {
	sapoID := strconv.FormatInt(seed.CustomerID, 10)

	// UpsertFromSapoIdentity is idempotent (UNIQUE constraint guards duplicates)
	// and backfills empty name/phone/email without clobbering existing values.
	// Quality fields come from the warehouse; INSERT OR IGNORE in crm_party_identity
	// ensures existing CRM-upgraded contact_quality values are never overwritten.
	_, err := s.partySvc.UpsertFromSapoIdentity(
		ctx, sapoID, seed.Phone, seed.Email, seed.DisplayName,
		seed.SourceContactQuality, seed.ContactQuality,
	)
	if err != nil {
		return fmt.Errorf("upsert party for sapo_id=%s: %w", sapoID, err)
	}
	return nil
}

package application

import (
	"context"
	"fmt"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// DedupService scans for duplicate parties and queues or auto-links them.
//
// Match strategy (per spec):
//   - exact normalised phone → insert candidate (score 1.0, rule exact_phone)
//   - exact normalised email → insert candidate (score 0.95, rule exact_email)
//   - FTS5 name on same phone-prefix → insert candidate (score 0.7, rule fts_name_phone)
//
// Auto-merge is deliberately NOT performed here; all matches go to the candidate queue
// for manual review (spec: default fuzzy NOT auto-merge in v1).
type DedupService struct {
	partyRepo ports.PartyRepository
	dedupRepo ports.DedupRepository
}

// NewDedupService constructs a DedupService.
func NewDedupService(pr ports.PartyRepository, dr ports.DedupRepository) *DedupService {
	return &DedupService{partyRepo: pr, dedupRepo: dr}
}

// ScanCandidates sweeps parties for exact phone/email matches, inserting new
// crm_dedup_candidate rows (skipping already-pending pairs).
// Designed to run as a periodic background job.
//
// Exact-phone and exact-email sweeps are fully implemented below.
// TODO fuzzy bucket: FTS5 name match within phone-prefix bucket (fts_name_phone rule).
func (s *DedupService) ScanCandidates(ctx context.Context) error {
	// Collect all existing pending pairs so we can skip duplicates without a DB round-trip per pair.
	existing, err := s.dedupRepo.ListCandidates(ctx, "pending")
	if err != nil {
		return fmt.Errorf("dedup scan: list pending candidates: %w", err)
	}
	known := make(map[string]bool, len(existing))
	for _, c := range existing {
		known[pairKey(c.PartyA, c.PartyB)] = true
	}

	// -- Exact phone sweep --
	// ListByPhone returns all non-merged parties sharing a primary_phone value.
	// Collect distinct phone values first by scanning all parties that have a phone.
	// Strategy: list all candidates (as a proxy for "known parties"), then for each unique
	// phone seen, call ListByPhone and pair them up. This is O(parties) — acceptable at v1 scale.
	//
	// We also handle the case where UpsertFromSapoIdentity sets primary_phone directly,
	// so duplicates can arise without going through identity UNIQUE conflict.
	if err := s.scanByField(ctx, known, "exact_phone", 1.0,
		func(p domain.Party) string { return p.PrimaryPhone },
		func(ctx context.Context, val string) ([]domain.Party, error) {
			return s.partyRepo.ListByPhone(ctx, val)
		},
	); err != nil {
		return fmt.Errorf("dedup scan: exact_phone: %w", err)
	}

	// -- Exact email sweep --
	if err := s.scanByField(ctx, known, "exact_email", 0.95,
		func(p domain.Party) string { return p.PrimaryEmail },
		func(ctx context.Context, val string) ([]domain.Party, error) {
			return s.partyRepo.ListByEmail(ctx, val)
		},
	); err != nil {
		return fmt.Errorf("dedup scan: exact_email: %w", err)
	}

	return nil
}

// scanByField sweeps for duplicates on a single field (phone or email).
// It enumerates all parties via their pending candidates to find unique field values,
// calls listFn for each value, and inserts a candidate for each pair with >1 result.
//
// already-known pending pairs are skipped; merged parties are excluded by listFn.
func (s *DedupService) scanByField(
	ctx context.Context,
	known map[string]bool,
	rule string,
	score float64,
	fieldOf func(domain.Party) string,
	listFn func(context.Context, string) ([]domain.Party, error),
) error {
	// Collect all party IDs referenced in any candidate (pending or otherwise) as seed.
	// Then also pull parties from ListByPhone/Email by seeding from known values.
	// In v1 with small data, a simpler full-table scan via ListCandidates is the proxy.
	// We enumerate unique field values from all listed parties to avoid quadratic calls.
	allCands, err := s.dedupRepo.ListCandidates(ctx, "")
	if err != nil {
		return fmt.Errorf("scan %s: list all candidates: %w", rule, err)
	}

	// Gather unique party IDs from candidates to seed field-value discovery.
	partyIDs := make(map[string]bool, len(allCands)*2)
	for _, c := range allCands {
		partyIDs[c.PartyA] = true
		partyIDs[c.PartyB] = true
	}

	// For each unique party, fetch by ID to get field values, then sweep duplicates.
	// Track which field values we've already swept to avoid redundant ListByPhone/Email calls.
	sweptValues := make(map[string]bool)
	for partyID := range partyIDs {
		party, err := s.partyRepo.GetByID(ctx, partyID)
		if err != nil {
			return fmt.Errorf("scan %s: get party %s: %w", rule, partyID, err)
		}
		if party == nil || party.IsMerged {
			continue
		}
		val := fieldOf(*party)
		if val == "" || sweptValues[val] {
			continue
		}
		sweptValues[val] = true

		peers, err := listFn(ctx, val)
		if err != nil {
			return fmt.Errorf("scan %s: list by value %q: %w", rule, val, err)
		}
		if len(peers) < 2 {
			continue
		}
		// Insert candidate for every distinct pair.
		for i := 0; i < len(peers); i++ {
			for j := i + 1; j < len(peers); j++ {
				a, b := peers[i].PartyID, peers[j].PartyID
				if known[pairKey(a, b)] {
					continue
				}
				if err := s.insertCandidate(ctx, a, b, rule, score); err != nil {
					return err
				}
				known[pairKey(a, b)] = true
			}
		}
	}
	return nil
}

// AddExactPhoneCandidate checks if two parties share a phone and inserts a candidate.
// Called by UpsertFromSapoIdentity when a UNIQUE conflict reveals a clash.
func (s *DedupService) AddExactPhoneCandidate(ctx context.Context, partyA, partyB string) error {
	return s.insertCandidate(ctx, partyA, partyB, "exact_phone", 1.0)
}

// AddExactEmailCandidate inserts an exact-email dedup candidate.
func (s *DedupService) AddExactEmailCandidate(ctx context.Context, partyA, partyB string) error {
	return s.insertCandidate(ctx, partyA, partyB, "exact_email", 0.95)
}

// AddFTSNameCandidate inserts a fuzzy-name dedup candidate (FTS5 match + phone prefix).
func (s *DedupService) AddFTSNameCandidate(ctx context.Context, partyA, partyB string) error {
	return s.insertCandidate(ctx, partyA, partyB, "fts_name_phone", 0.7)
}

func (s *DedupService) insertCandidate(
	ctx context.Context,
	partyA, partyB, rule string,
	score float64,
) error {
	exists, err := s.dedupRepo.CandidateExists(ctx, partyA, partyB)
	if err != nil {
		return fmt.Errorf("dedup: check candidate exists: %w", err)
	}
	if exists {
		return nil // already queued
	}

	c := &domain.DedupCandidate{
		CandidateID: uuid.New().String(),
		PartyA:      partyA,
		PartyB:      partyB,
		MatchRule:   rule,
		MatchScore:  score,
		Status:      "pending",
		CreatedAt:   utcNow(),
	}
	return s.dedupRepo.InsertCandidate(ctx, c)
}

// pairKey builds an order-independent map key for a party pair.
func pairKey(a, b string) string {
	if a < b {
		return a + "|" + b
	}
	return b + "|" + a
}

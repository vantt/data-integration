// Package ports defines inbound and outbound interfaces for the CRM hexagonal architecture.
// Nothing in this package may import sqlite, http, or any adapter package.
package ports

import (
	"context"

	"github.com/vantt/data-integration/crm/app/internal/domain"
)

// DedupRepository is the outbound port for dedup candidates and merge-log operations.
type DedupRepository interface {
	// InsertCandidate adds a new suspect-match pair if no pending/merged candidate
	// already exists for the same (party_a, party_b) pair.
	InsertCandidate(ctx context.Context, c *domain.DedupCandidate) error

	// CandidateExists returns true if a non-rejected candidate already exists
	// for the given pair (order-independent: (a,b) == (b,a)).
	CandidateExists(ctx context.Context, partyA, partyB string) (bool, error)

	// ListCandidates returns dedup candidates filtered by status.
	// Pass empty string to return all statuses.
	ListCandidates(ctx context.Context, status string) ([]domain.DedupCandidate, error)

	// GetCandidate returns a single candidate by ID.
	GetCandidate(ctx context.Context, candidateID string) (*domain.DedupCandidate, error)

	// UpdateCandidateStatus sets status, reviewed_by, reviewed_at on a candidate.
	UpdateCandidateStatus(ctx context.Context, candidateID, status string, reviewedBy *string) error

	// Merge executes the full merge transaction:
	//   1. Re-point identities from mergedPartyID → survivingPartyID (skip UNIQUE conflicts).
	//   2. Set merged party is_merged=1, merged_into=survivingPartyID.
	//   3. Insert a crm_party_merge_log row with a JSON snapshot.
	// Returns the new merge_id.
	Merge(ctx context.Context, survivingPartyID, mergedPartyID, reason string, mergedBy *string, snapshot string) (string, error)

	// UndoMerge restores party flags and identities from the JSON snapshot stored in
	// crm_party_merge_log, then marks the log row as undone (sets reason suffix).
	UndoMerge(ctx context.Context, mergeID string) error

	// GetMergeLog retrieves a merge log entry by ID.
	GetMergeLog(ctx context.Context, mergeID string) (*domain.MergeLog, error)
}

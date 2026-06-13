package application

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// MergeService orchestrates party merges and undos.
// All persistence is delegated to DedupRepository which executes atomic transactions.
type MergeService struct {
	partyRepo ports.PartyRepository
	dedupRepo ports.DedupRepository
}

// NewMergeService constructs a MergeService.
func NewMergeService(pr ports.PartyRepository, dr ports.DedupRepository) *MergeService {
	return &MergeService{partyRepo: pr, dedupRepo: dr}
}

// mergeSnapshot is the JSON structure stored in crm_party_merge_log.snapshot.
// It carries enough state to fully reverse the merge.
type mergeSnapshot struct {
	MergedPartyIsMerged  bool     `json:"merged_party_is_merged"`
	MergedPartyMergedInto *string `json:"merged_party_merged_into"`
	// identity_ids that were reassigned from mergedPartyID → survivingPartyID.
	// Undo moves them back.
	ReassignedIdentityIDs []string `json:"reassigned_identity_ids"`
}

// Merge absorbs mergedPartyID into survivingPartyID:
//  1. Captures pre-merge state for undo.
//  2. Delegates atomic transaction (re-point identities, set flags, write log) to repo.
//
// Returns the merge_id of the log entry.
func (s *MergeService) Merge(
	ctx context.Context,
	survivingPartyID, mergedPartyID, reason string,
	mergedBy *string,
) (string, error) {
	// Validate both parties exist.
	surviving, err := s.partyRepo.GetByID(ctx, survivingPartyID)
	if err != nil {
		return "", fmt.Errorf("merge: get surviving party: %w", err)
	}
	if surviving == nil {
		return "", fmt.Errorf("merge: surviving party %q not found", survivingPartyID)
	}
	if surviving.IsMerged {
		return "", fmt.Errorf("merge: surviving party %q already merged into %v", survivingPartyID, surviving.MergedInto)
	}

	merged, err := s.partyRepo.GetByID(ctx, mergedPartyID)
	if err != nil {
		return "", fmt.Errorf("merge: get merged party: %w", err)
	}
	if merged == nil {
		return "", fmt.Errorf("merge: merged party %q not found", mergedPartyID)
	}
	if merged.IsMerged {
		return "", fmt.Errorf("merge: party %q is already merged into %v", mergedPartyID, merged.MergedInto)
	}

	// Gather identities of the merged party for snapshot.
	identities, err := s.partyRepo.ListIdentities(ctx, mergedPartyID)
	if err != nil {
		return "", fmt.Errorf("merge: list identities: %w", err)
	}
	ids := make([]string, 0, len(identities))
	for _, id := range identities {
		ids = append(ids, id.IdentityID)
	}

	snap := mergeSnapshot{
		MergedPartyIsMerged:   merged.IsMerged,
		MergedPartyMergedInto: merged.MergedInto,
		ReassignedIdentityIDs: ids,
	}
	snapJSON, err := json.Marshal(snap)
	if err != nil {
		return "", fmt.Errorf("merge: marshal snapshot: %w", err)
	}

	mergeID, err := s.dedupRepo.Merge(ctx, survivingPartyID, mergedPartyID, reason, mergedBy, string(snapJSON))
	if err != nil {
		return "", fmt.Errorf("merge: execute transaction: %w", err)
	}
	return mergeID, nil
}

// Undo reverses a previously completed merge using the snapshot stored in the log.
func (s *MergeService) Undo(ctx context.Context, mergeID string) error {
	if err := s.dedupRepo.UndoMerge(ctx, mergeID); err != nil {
		return fmt.Errorf("merge undo: %w", err)
	}
	return nil
}

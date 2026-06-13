// Package sqlite — DedupRepository adapter.
// Implements ports.DedupRepository; merge/undo run as atomic transactions via SQLDB().BeginTx.
package sqlite

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/google/uuid"

	"github.com/vantt/data-integration/crm/app/internal/adapters/outbound/sqlite/sqlcgen"
	"github.com/vantt/data-integration/crm/app/internal/domain"
	"github.com/vantt/data-integration/crm/app/internal/ports"
)

// DedupRepo satisfies ports.DedupRepository.
type DedupRepo struct {
	db *DB
	q  *sqlcgen.Queries
}

// NewDedupRepo constructs a DedupRepo.
func NewDedupRepo(db *DB) ports.DedupRepository {
	return &DedupRepo{db: db, q: sqlcgen.New(db.SQLDB())}
}

func (r *DedupRepo) InsertCandidate(ctx context.Context, c *domain.DedupCandidate) error {
	err := r.q.InsertDedupCandidate(ctx, sqlcgen.InsertDedupCandidateParams{
		CandidateID: c.CandidateID,
		PartyA:      c.PartyA,
		PartyB:      c.PartyB,
		MatchRule:   c.MatchRule,
		MatchScore:  c.MatchScore,
		Status:      c.Status,
		CreatedAt:   c.CreatedAt,
	})
	if err != nil {
		return fmt.Errorf("dedup repo: insert candidate: %w", err)
	}
	return nil
}

func (r *DedupRepo) CandidateExists(ctx context.Context, partyA, partyB string) (bool, error) {
	count, err := r.q.DedupCandidateExists(ctx, sqlcgen.DedupCandidateExistsParams{
		PartyA:   partyA,
		PartyB:   partyB,
		PartyA_2: partyB, // reversed pair
		PartyB_2: partyA,
	})
	if err != nil {
		return false, fmt.Errorf("dedup repo: candidate exists: %w", err)
	}
	return count > 0, nil
}

func (r *DedupRepo) ListCandidates(ctx context.Context, status string) ([]domain.DedupCandidate, error) {
	var rows []sqlcgen.CrmDedupCandidate
	var err error
	if status == "" {
		rows, err = r.q.ListAllDedupCandidates(ctx)
	} else {
		rows, err = r.q.ListDedupCandidatesByStatus(ctx, status)
	}
	if err != nil {
		return nil, fmt.Errorf("dedup repo: list candidates: %w", err)
	}
	out := make([]domain.DedupCandidate, 0, len(rows))
	for _, row := range rows {
		out = append(out, rowToCandidate(row))
	}
	return out, nil
}

func (r *DedupRepo) GetCandidate(ctx context.Context, candidateID string) (*domain.DedupCandidate, error) {
	row, err := r.q.GetDedupCandidate(ctx, candidateID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("dedup repo: get candidate: %w", err)
	}
	c := rowToCandidate(row)
	return &c, nil
}

func (r *DedupRepo) UpdateCandidateStatus(ctx context.Context, candidateID, status string, reviewedBy *string) error {
	err := r.q.UpdateDedupCandidateStatus(ctx, sqlcgen.UpdateDedupCandidateStatusParams{
		CandidateID: candidateID,
		Status:      status,
		ReviewedBy:  toNullStringPtr(reviewedBy),
	})
	if err != nil {
		return fmt.Errorf("dedup repo: update candidate status: %w", err)
	}
	return nil
}

// Merge runs the full merge transaction atomically:
//  1. For each identity of mergedPartyID → reassign to survivingPartyID.
//  2. Set merged party is_merged=1, merged_into=survivingPartyID.
//  3. Insert crm_party_merge_log with the caller-supplied JSON snapshot.
func (r *DedupRepo) Merge(
	ctx context.Context,
	survivingPartyID, mergedPartyID, reason string,
	mergedBy *string,
	snapshot string,
) (string, error) {
	mergeID := uuid.New().String()

	tx, err := r.db.SQLDB().BeginTx(ctx, nil)
	if err != nil {
		return "", fmt.Errorf("dedup repo: begin merge tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	qtx := sqlcgen.New(tx)

	// 1. Gather identities of the merged party.
	identities, err := qtx.ListIdentitiesByParty(ctx, mergedPartyID)
	if err != nil {
		return "", fmt.Errorf("dedup repo: list merged identities: %w", err)
	}

	// 2. Reassign each identity to the surviving party.
	// UNIQUE(identity_type, identity_value) cannot fire on a party_id-only update,
	// so any error here is a real I/O or ctx-cancel failure — propagate it.
	for _, id := range identities {
		if err := reassignIdentity(ctx, tx, id.IdentityID, survivingPartyID); err != nil {
			return "", fmt.Errorf("dedup repo: reassign identity %s: %w", id.IdentityID, err)
		}
	}

	// 3. Mark merged party.
	_, err = tx.ExecContext(ctx,
		`UPDATE crm_party SET is_merged=1, merged_into=? WHERE party_id=?`,
		survivingPartyID, mergedPartyID,
	)
	if err != nil {
		return "", fmt.Errorf("dedup repo: mark merged party: %w", err)
	}

	// 4. Insert merge log.
	if err := qtx.InsertMergeLog(ctx, sqlcgen.InsertMergeLogParams{
		MergeID:          mergeID,
		SurvivingPartyID: survivingPartyID,
		MergedPartyID:    mergedPartyID,
		Reason:           toNullString(reason),
		MergedBy:         toNullStringPtr(mergedBy),
		Snapshot:         toNullString(snapshot),
	}); err != nil {
		return "", fmt.Errorf("dedup repo: insert merge log: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return "", fmt.Errorf("dedup repo: commit merge tx: %w", err)
	}
	return mergeID, nil
}

// UndoMerge restores identities and merged flags from the JSON snapshot in the log entry.
// Returns an error if the merge has already been undone (double-undo guard).
func (r *DedupRepo) UndoMerge(ctx context.Context, mergeID string) error {
	log, err := r.q.GetMergeLog(ctx, mergeID)
	if errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("dedup repo: merge log %q not found", mergeID)
	}
	if err != nil {
		return fmt.Errorf("dedup repo: get merge log: %w", err)
	}

	// Double-undo guard: reject if undone_at is already set.
	if log.UndonAt.Valid {
		return fmt.Errorf("merge %q already undone", mergeID)
	}

	if !log.Snapshot.Valid || log.Snapshot.String == "" {
		return fmt.Errorf("dedup repo: merge %q has no snapshot — cannot undo", mergeID)
	}

	var snap struct {
		MergedPartyIsMerged   bool     `json:"merged_party_is_merged"`
		MergedPartyMergedInto *string  `json:"merged_party_merged_into"`
		ReassignedIdentityIDs []string `json:"reassigned_identity_ids"`
	}
	if err := json.Unmarshal([]byte(log.Snapshot.String), &snap); err != nil {
		return fmt.Errorf("dedup repo: unmarshal snapshot: %w", err)
	}

	tx, err := r.db.SQLDB().BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("dedup repo: begin undo tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	// Restore identities back to the previously-merged party.
	for _, identityID := range snap.ReassignedIdentityIDs {
		if err := reassignIdentity(ctx, tx, identityID, log.MergedPartyID); err != nil {
			return fmt.Errorf("dedup repo: undo reassign identity %s: %w", identityID, err)
		}
	}

	// Restore merged party flags.
	isMerged := boolToInt(snap.MergedPartyIsMerged)
	_, err = tx.ExecContext(ctx,
		`UPDATE crm_party SET is_merged=?, merged_into=? WHERE party_id=?`,
		isMerged, snap.MergedPartyMergedInto, log.MergedPartyID,
	)
	if err != nil {
		return fmt.Errorf("dedup repo: restore merged party flags: %w", err)
	}

	// Stamp undone_at to prevent future double-undo.
	_, err = tx.ExecContext(ctx,
		`UPDATE crm_party_merge_log SET undone_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE merge_id=?`,
		mergeID,
	)
	if err != nil {
		return fmt.Errorf("dedup repo: stamp undone_at: %w", err)
	}

	return tx.Commit()
}

func (r *DedupRepo) GetMergeLog(ctx context.Context, mergeID string) (*domain.MergeLog, error) {
	row, err := r.q.GetMergeLog(ctx, mergeID)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("dedup repo: get merge log: %w", err)
	}
	return rowToMergeLog(row), nil
}

// reassignIdentity updates party_id on an identity row inside a transaction.
// Any error (I/O, ctx-cancel) is propagated — callers must handle it.
// Note: UNIQUE(identity_type, identity_value) cannot fire on a party_id-only update.
func reassignIdentity(ctx context.Context, tx *sql.Tx, identityID, toPartyID string) error {
	_, err := tx.ExecContext(ctx,
		`UPDATE crm_party_identity SET party_id=? WHERE identity_id=?`,
		toPartyID, identityID,
	)
	return err
}

// --- mapping helpers ---

func rowToCandidate(r sqlcgen.CrmDedupCandidate) domain.DedupCandidate {
	c := domain.DedupCandidate{
		CandidateID: r.CandidateID,
		PartyA:      r.PartyA,
		PartyB:      r.PartyB,
		MatchRule:   r.MatchRule,
		MatchScore:  r.MatchScore,
		Status:      r.Status,
		CreatedAt:   r.CreatedAt,
	}
	if r.ReviewedBy.Valid {
		s := r.ReviewedBy.String
		c.ReviewedBy = &s
	}
	if r.ReviewedAt.Valid {
		s := r.ReviewedAt.String
		c.ReviewedAt = &s
	}
	return c
}

func rowToMergeLog(r sqlcgen.CrmPartyMergeLog) *domain.MergeLog {
	m := &domain.MergeLog{
		MergeID:          r.MergeID,
		SurvivingPartyID: r.SurvivingPartyID,
		MergedPartyID:    r.MergedPartyID,
		Reason:           r.Reason.String,
		Snapshot:         r.Snapshot.String,
		MergedAt:         r.MergedAt,
	}
	if r.MergedBy.Valid {
		s := r.MergedBy.String
		m.MergedBy = &s
	}
	return m
}

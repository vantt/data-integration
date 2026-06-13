-- Dedup candidate and merge log queries

-- name: InsertDedupCandidate :exec
INSERT INTO crm_dedup_candidate (
  candidate_id, party_a, party_b, match_rule, match_score, status, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?);

-- name: DedupCandidateExists :one
-- Only a 'pending' candidate blocks re-detection; merged/rejected pairs can be re-scanned.
SELECT COUNT(*) FROM crm_dedup_candidate
WHERE status = 'pending'
  AND (
    (party_a = ? AND party_b = ?)
    OR
    (party_a = ? AND party_b = ?)
  );

-- name: ListDedupCandidatesByStatus :many
SELECT candidate_id, party_a, party_b, match_rule, match_score,
       status, reviewed_by, reviewed_at, created_at
FROM crm_dedup_candidate
WHERE status = ?
ORDER BY match_score DESC, created_at;

-- name: ListAllDedupCandidates :many
SELECT candidate_id, party_a, party_b, match_rule, match_score,
       status, reviewed_by, reviewed_at, created_at
FROM crm_dedup_candidate
ORDER BY match_score DESC, created_at;

-- name: GetDedupCandidate :one
SELECT candidate_id, party_a, party_b, match_rule, match_score,
       status, reviewed_by, reviewed_at, created_at
FROM crm_dedup_candidate
WHERE candidate_id = ?
LIMIT 1;

-- name: UpdateDedupCandidateStatus :exec
UPDATE crm_dedup_candidate
SET status      = ?,
    reviewed_by = ?,
    reviewed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
WHERE candidate_id = ?;

-- Merge log queries

-- name: InsertMergeLog :exec
INSERT INTO crm_party_merge_log (
  merge_id, surviving_party_id, merged_party_id, reason, merged_by, snapshot, merged_at
) VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));

-- name: GetMergeLog :one
SELECT merge_id, surviving_party_id, merged_party_id, reason, merged_by, snapshot, merged_at, undone_at
FROM crm_party_merge_log
WHERE merge_id = ?
LIMIT 1;

-- name: UpdateMergeLogReason :exec
UPDATE crm_party_merge_log
SET reason = ?
WHERE merge_id = ?;

-- Segment queries (crm_segment, crm_segment_member)

-- name: InsertSegment :exec
INSERT INTO crm_segment (
  segment_id, name, description, is_dynamic, definition, owner_user_id, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?);

-- name: GetSegmentByID :one
SELECT
  segment_id, name, description, is_dynamic, definition, owner_user_id, created_at, updated_at
FROM crm_segment
WHERE segment_id = ?;

-- name: UpdateSegment :exec
UPDATE crm_segment
SET
  name          = ?,
  description   = ?,
  is_dynamic    = ?,
  definition    = ?,
  owner_user_id = ?,
  updated_at    = ?
WHERE segment_id = ?;

-- name: ListSegments :many
SELECT
  segment_id, name, description, is_dynamic, definition, owner_user_id, created_at, updated_at
FROM crm_segment
ORDER BY created_at DESC;

-- name: UpsertSegmentMember :exec
INSERT INTO crm_segment_member (segment_id, party_id, source, added_at)
VALUES (?, ?, ?, ?)
ON CONFLICT (segment_id, party_id) DO UPDATE SET
  source   = CASE WHEN crm_segment_member.source = 'manual' THEN 'manual' ELSE excluded.source END,
  added_at = excluded.added_at;

-- name: DeleteSegmentMember :exec
DELETE FROM crm_segment_member
WHERE segment_id = ? AND party_id = ?;

-- name: ListSegmentMembers :many
SELECT segment_id, party_id, source, added_at
FROM crm_segment_member
WHERE segment_id = ?
ORDER BY added_at DESC;

-- name: DeleteRuleSegmentMembers :exec
DELETE FROM crm_segment_member
WHERE segment_id = ? AND source = 'rule';

-- Activity queries (crm_activity)

-- name: InsertActivity :exec
INSERT INTO crm_activity (
  activity_id, party_id, activity_type, direction, channel,
  subject, body, outcome, related_order_code,
  staff_user_id, occurred_at, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

-- name: ListActivitiesByParty :many
SELECT
  activity_id, party_id, activity_type, direction, channel,
  subject, body, outcome, related_order_code,
  staff_user_id, occurred_at, created_at
FROM crm_activity
WHERE party_id = ?
ORDER BY occurred_at DESC;

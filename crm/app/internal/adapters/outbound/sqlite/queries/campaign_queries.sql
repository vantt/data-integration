-- Campaign queries (crm_campaign, crm_campaign_target)

-- name: InsertCampaign :exec
INSERT INTO crm_campaign (
  campaign_id, name, objective, channel, segment_id, status, scheduled_at, created_by, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

-- name: GetCampaignByID :one
SELECT
  campaign_id, name, objective, channel, segment_id, status, scheduled_at, created_by, created_at, updated_at
FROM crm_campaign
WHERE campaign_id = ?;

-- name: UpdateCampaign :exec
UPDATE crm_campaign
SET
  name         = ?,
  objective    = ?,
  channel      = ?,
  segment_id   = ?,
  status       = ?,
  scheduled_at = ?,
  updated_at   = ?
WHERE campaign_id = ?;

-- name: ListCampaigns :many
SELECT
  campaign_id, name, objective, channel, segment_id, status, scheduled_at, created_by, created_at, updated_at
FROM crm_campaign
ORDER BY created_at DESC;

-- name: UpsertCampaignTarget :exec
INSERT INTO crm_campaign_target (
  campaign_id, party_id, status, assigned_user_id, last_touch_at,
  converted_order_code, converted_revenue_vnd, converted_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (campaign_id, party_id) DO NOTHING;

-- name: UpdateCampaignTarget :exec
UPDATE crm_campaign_target
SET
  status                = ?,
  assigned_user_id      = ?,
  last_touch_at         = ?,
  converted_order_code  = ?,
  converted_revenue_vnd = ?,
  converted_at          = ?
WHERE campaign_id = ? AND party_id = ?;

-- name: GetCampaignTarget :one
SELECT
  campaign_id, party_id, status, assigned_user_id, last_touch_at,
  converted_order_code, converted_revenue_vnd, converted_at
FROM crm_campaign_target
WHERE campaign_id = ? AND party_id = ?;

-- name: ListCampaignTargets :many
SELECT
  campaign_id, party_id, status, assigned_user_id, last_touch_at,
  converted_order_code, converted_revenue_vnd, converted_at
FROM crm_campaign_target
WHERE campaign_id = ?
ORDER BY party_id;

-- name: ListCampaignTargetsByStatus :many
SELECT
  campaign_id, party_id, status, assigned_user_id, last_touch_at,
  converted_order_code, converted_revenue_vnd, converted_at
FROM crm_campaign_target
WHERE campaign_id = ? AND status = ?
ORDER BY party_id;

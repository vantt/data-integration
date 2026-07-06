-- Migration 0038 DOWN: drop the (party_id, action_type) TTL dismissal table.
DROP INDEX IF EXISTS idx_action_dismissal_until;
DROP TABLE IF EXISTS crm_action_dismissal;

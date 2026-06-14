-- Migration 0005 DOWN: drop segments + campaigns tables (reverse of 0005 UP)

DROP TRIGGER IF EXISTS trg_campaign_touch;
DROP INDEX IF EXISTS idx_campaign_target_assignee_status;
DROP TABLE IF EXISTS crm_campaign_target;

DROP INDEX IF EXISTS idx_campaign_segment;
DROP TABLE IF EXISTS crm_campaign;

DROP INDEX IF EXISTS idx_segment_member_party;
DROP TABLE IF EXISTS crm_segment_member;

DROP TRIGGER IF EXISTS trg_segment_touch;
DROP TABLE IF EXISTS crm_segment;

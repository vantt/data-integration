-- Migration 0024 DOWN: remove crm_hug_campaign tables and indexes
DROP INDEX IF EXISTS idx_crm_hug_campaign_history_lookup;
DROP TABLE IF EXISTS crm_hug_campaign_history;
DROP INDEX IF EXISTS idx_crm_hug_campaign_status_priority;
DROP TABLE IF EXISTS crm_hug_campaign;

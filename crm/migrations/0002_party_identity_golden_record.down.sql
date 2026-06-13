-- Migration 0002 DOWN: drop party identity tables and FTS5 in reverse dependency order

DROP TRIGGER IF EXISTS trg_party_fts_delete;
DROP TRIGGER IF EXISTS trg_party_fts_update;
DROP TRIGGER IF EXISTS trg_party_fts_insert;
DROP VIRTUAL TABLE IF EXISTS crm_party_fts;

DROP INDEX IF EXISTS idx_dedup_status;
DROP INDEX IF EXISTS idx_identity_value;
DROP INDEX IF EXISTS idx_party_phone;

DROP TABLE IF EXISTS crm_party_merge_log;
DROP TABLE IF EXISTS crm_dedup_candidate;
DROP TABLE IF EXISTS crm_party_identity;

DROP TRIGGER IF EXISTS trg_party_touch;
DROP TABLE IF EXISTS crm_party;

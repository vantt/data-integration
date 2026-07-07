-- Migration 0039 DOWN: drop tag ACL tables and revert crm_party_tag extension.
-- SQLite 3.46 (in-use version, verified >= 3.35) supports DROP COLUMN directly —
-- same approach as migration 0035 (crm_activity_log.outcome_reason).
DROP INDEX IF EXISTS idx_party_tag_source_party;
ALTER TABLE crm_party_tag DROP COLUMN ext_ref;
ALTER TABLE crm_party_tag DROP COLUMN source;

DROP INDEX IF EXISTS idx_ext_tag_map_active;
DROP TABLE IF EXISTS crm_ext_tag_map;
DROP TABLE IF EXISTS crm_ext_tag;

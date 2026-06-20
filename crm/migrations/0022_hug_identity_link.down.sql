-- Migration 0022 DOWN: remove hug_identity_link table and its indexes
DROP INDEX IF EXISTS idx_identity_link_resolved;
DROP INDEX IF EXISTS idx_identity_link_token;
DROP INDEX IF EXISTS idx_identity_link_status;
DROP TABLE IF EXISTS crm_identity_link;

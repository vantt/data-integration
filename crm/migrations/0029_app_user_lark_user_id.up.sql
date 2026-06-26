-- Migration 0029 UP: add lark_user_id to crm_app_user
-- Stores Lark open_id (ou_...) sourced from CF Access JWT custom.sub claim.
-- "duplicate column name" error is silently swallowed by the migration runner (idempotent).

ALTER TABLE crm_app_user ADD COLUMN lark_user_id TEXT;

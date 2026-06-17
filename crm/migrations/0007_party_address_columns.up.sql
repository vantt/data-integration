-- Migration 0007 UP: structured address fields on crm_party
-- Replaces the crm_customer_profile.address JSON blob (kept for migration compat, ignored going forward)
-- R13: address_source distinguishes sapo_sync (sync may overwrite) vs manual (sync must NOT overwrite)

ALTER TABLE crm_party ADD COLUMN address_line       TEXT;
ALTER TABLE crm_party ADD COLUMN ward               TEXT;
ALTER TABLE crm_party ADD COLUMN district           TEXT;
ALTER TABLE crm_party ADD COLUMN province           TEXT;
ALTER TABLE crm_party ADD COLUMN address_source     TEXT NOT NULL DEFAULT 'sapo_sync';
  -- sapo_sync | manual
ALTER TABLE crm_party ADD COLUMN address_note       TEXT;
ALTER TABLE crm_party ADD COLUMN address_updated_at TEXT;
ALTER TABLE crm_party ADD COLUMN address_updated_by TEXT REFERENCES crm_app_user(user_id);

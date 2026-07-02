-- Migration 0032 UP: add task_kind + channel columns to crm_task
-- task_kind classifies tasks as contact|internal|generic.
-- DEFAULT 'contact' fills ALL existing rows immediately (no NULL window).
-- Subsequent UPDATEs reclassify the two special cases within crm.db itself —
-- no join to cache / warehouse data is needed because:
--   - generic: party_id IS NULL (admin/no-customer tasks)
--   - internal: verify_account signals live in crm_task.source / source_ref / title
ALTER TABLE crm_task ADD COLUMN task_kind TEXT NOT NULL DEFAULT 'contact';
ALTER TABLE crm_task ADD COLUMN channel TEXT;
UPDATE crm_task SET task_kind='generic' WHERE party_id IS NULL;
UPDATE crm_task SET task_kind='internal' WHERE source='verify_account' OR source_ref LIKE 'verify_account%' OR lower(title) LIKE '%xác minh tài khoản%';

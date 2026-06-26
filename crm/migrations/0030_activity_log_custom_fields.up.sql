-- Migration 0030 UP: add custom_fields JSON column to crm_activity_log
-- Stores structured metadata (owner_user_id, etc.) separate from display subject.
ALTER TABLE crm_activity_log ADD COLUMN custom_fields TEXT;

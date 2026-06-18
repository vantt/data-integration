ALTER TABLE crm_note ADD COLUMN source_activity_id TEXT REFERENCES crm_activity(activity_id);
CREATE INDEX IF NOT EXISTS idx_note_source_activity ON crm_note(source_activity_id);

-- Migration 0010 UP: note type classification, pinning, visibility, task/campaign linkage
-- Enables P05 (Notes Panel) type tabs and M08 (Log Activity) contact_attempt mode
-- note_type drives where notes surface: contact_pref on S01 worklist, warning on S03 left col

ALTER TABLE crm_note ADD COLUMN note_type          TEXT NOT NULL DEFAULT 'general';
  -- general | preference | contact_pref | warning | outcome | internal
ALTER TABLE crm_note ADD COLUMN pinned             INTEGER NOT NULL DEFAULT 0;
ALTER TABLE crm_note ADD COLUMN pinned_until       TEXT;
  -- UTC ISO-8601, NULL = permanent pin
ALTER TABLE crm_note ADD COLUMN visibility         TEXT NOT NULL DEFAULT 'team';
  -- team | private
ALTER TABLE crm_note ADD COLUMN task_id            TEXT REFERENCES crm_task(task_id);
  -- links note to the task it was logged against (retail activation chain)
ALTER TABLE crm_note ADD COLUMN campaign_id        TEXT REFERENCES crm_campaign(campaign_id);
ALTER TABLE crm_note ADD COLUMN updated_at         TEXT;
ALTER TABLE crm_note ADD COLUMN updated_by_user_id TEXT REFERENCES crm_app_user(user_id);
ALTER TABLE crm_note ADD COLUMN deleted_at         TEXT;
  -- soft delete; app filters WHERE deleted_at IS NULL

CREATE INDEX IF NOT EXISTS idx_note_party_type
  ON crm_note (party_id, note_type);

CREATE INDEX IF NOT EXISTS idx_note_party_pinned
  ON crm_note (party_id, pinned);

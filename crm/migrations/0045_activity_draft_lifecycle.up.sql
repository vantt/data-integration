-- Migration 0045 UP: draft lifecycle for crm_activity_log (activity-log disposition API).
--
-- status:              'draft'|'final'; NULL = final (safe default for every row written
--                       before this migration — legacy insert path never set a status).
-- started_at:          UTC ISO-8601; stamped when a draft is created (call-session start).
-- finalize_at:         UTC ISO-8601; stamped when finalize() runs.
-- contact_duration_s:  finalize_at - started_at in seconds, auto-computed at finalize;
--                       staff can override manually in M08 (manual entry wins).
ALTER TABLE crm_activity_log ADD COLUMN status TEXT;
ALTER TABLE crm_activity_log ADD COLUMN started_at TEXT;
ALTER TABLE crm_activity_log ADD COLUMN finalize_at TEXT;
ALTER TABLE crm_activity_log ADD COLUMN contact_duration_s INTEGER;

-- One open draft per (staff, party) — enforced at the application layer (find-or-create
-- in ActivityService.create_draft), this partial index just makes that lookup O(log n)
-- instead of a full scan as call volume grows.
CREATE INDEX IF NOT EXISTS idx_activity_log_open_draft
  ON crm_activity_log (staff_user_id, party_id)
  WHERE status = 'draft';

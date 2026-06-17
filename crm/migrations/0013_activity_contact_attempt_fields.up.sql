-- Migration 0013 UP: contact attempt detail fields on crm_activity
-- Links activities to their parent task (retail activation chain: task → activity → note)
-- contact_outcome = per-attempt result; crm_task.outcome (0012) = final task resolution

ALTER TABLE crm_activity ADD COLUMN task_id           TEXT REFERENCES crm_task(task_id);
ALTER TABLE crm_activity ADD COLUMN channel_used      TEXT;
  -- phone | zalo | messenger | store | email
ALTER TABLE crm_activity ADD COLUMN contact_outcome   TEXT;
  -- reached | no_answer | callback | refused
ALTER TABLE crm_activity ADD COLUMN callback_at       TEXT;
  -- UTC ISO-8601, set when contact_outcome = 'callback'
ALTER TABLE crm_activity ADD COLUMN contact_duration_s INTEGER;
  -- call duration seconds (nullable, only meaningful for phone)

CREATE INDEX IF NOT EXISTS idx_activity_task
  ON crm_activity (task_id) WHERE task_id IS NOT NULL;

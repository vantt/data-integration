-- Migration 0034 UP: missing indexes for activity log, task, and campaign target

-- Staff activity coaching (high-frequency: "100 most-recent activities for staff X")
CREATE INDEX IF NOT EXISTS idx_activity_log_staff_occurred
  ON crm_activity_log (staff_user_id, occurred_at DESC);

-- Task lookup per customer (action queue: "open tasks for customer X")
CREATE INDEX IF NOT EXISTS idx_task_party_status
  ON crm_task (party_id, status);

-- Campaign target progress (campaign admin: "count targets by status per campaign")
CREATE INDEX IF NOT EXISTS idx_hug_target_campaign_state
  ON crm_campaign_target (campaign_id, status);

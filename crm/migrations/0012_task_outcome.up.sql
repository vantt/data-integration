-- Migration 0012 UP: task outcome for retail activation resolution tracking
-- outcome set when task moves to done/cancelled — records final result of the outreach
-- Per-attempt outcomes (reached/no_answer/...) live on crm_activity.contact_outcome (0013)

ALTER TABLE crm_task ADD COLUMN outcome TEXT;
  -- converted | follow_up | refused | invalid_contact | NULL (still open)

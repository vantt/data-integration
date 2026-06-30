-- Migration 0030 UP: enforce uniqueness on crm_app_user.staff_id (Sapo account_id bridge)
-- staff_id already exists (migration 0001) but was never constrained.
-- Partial index excludes NULLs: staff who have not yet synced Sapo ID are not affected.

CREATE UNIQUE INDEX IF NOT EXISTS uidx_app_user_staff_id
  ON crm_app_user (staff_id) WHERE staff_id IS NOT NULL;

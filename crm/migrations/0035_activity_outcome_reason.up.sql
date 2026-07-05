-- Migration 0035 UP: structured outcome_reason for activity log (D2 Phase 03)
-- contact_outcome (added 0013) is already present.
-- outcome_reason: nullable; required by server when contact_outcome = 'refused'.
-- Pilot: enum set reviewed after 2 weeks before locking mart mapping (design §8.3).
ALTER TABLE crm_activity_log ADD COLUMN outcome_reason TEXT;

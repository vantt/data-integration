-- Migration 0036 UP: persist action-queue context on task at claim time (A1 Phase 04)
ALTER TABLE crm_task ADD COLUMN value_at_stake_vnd INTEGER;
ALTER TABLE crm_task ADD COLUMN top_affinity_product TEXT;

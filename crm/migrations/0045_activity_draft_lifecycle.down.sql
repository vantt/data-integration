-- Migration 0045 DOWN: SQLite pre-3.35 cannot DROP COLUMN; forward-fix preferred.
-- No-op for columns (see 0032_task_kind.down.sql / 0043 convention) — drop the index only.
DROP INDEX IF EXISTS idx_activity_log_open_draft;

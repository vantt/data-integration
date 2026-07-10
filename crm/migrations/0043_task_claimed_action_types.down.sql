-- Migration 0043 DOWN: SQLite pre-3.35 cannot DROP COLUMN; forward-fix preferred.
-- No-op — column removal requires table rebuild if needed (see 0032_task_kind.down.sql).
SELECT 1;

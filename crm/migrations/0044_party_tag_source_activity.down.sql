-- Migration 0044 DOWN: SQLite pre-3.35 cannot DROP COLUMN; forward-fix preferred.
-- No-op — column removal requires table rebuild if needed (see 0032_task_kind.down.sql).
DROP INDEX IF EXISTS idx_party_tag_source_activity;

-- Migration 0032 DOWN: SQLite pre-3.35 cannot DROP COLUMN; forward-fix preferred.
-- No-op — column removal requires table rebuild if needed.
SELECT 1;

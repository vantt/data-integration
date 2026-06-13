-- Migration 0001 UP: crm_app_user table, trigger, and seed admin
-- SQLite dialect — UTC ISO-8601 timestamps, UUID as TEXT

CREATE TABLE IF NOT EXISTS crm_app_user (
  user_id    TEXT PRIMARY KEY,
  staff_id   INTEGER,
  email      TEXT UNIQUE NOT NULL,
  full_name  TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'sales',
  is_active  INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS trg_app_user_touch
AFTER UPDATE ON crm_app_user
BEGIN
  UPDATE crm_app_user
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

-- Seed: deterministic admin user
INSERT OR IGNORE INTO crm_app_user (user_id, email, full_name, role, is_active)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'admin@crm.local',
  'System Admin',
  'admin',
  1
);

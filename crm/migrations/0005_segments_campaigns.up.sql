-- Migration 0005 UP: segments + reactivation campaigns
-- SQLite dialect — TEXT uuid (app-generated), TEXT UTC ISO-8601, INTEGER bool/money(VND), crm_* prefix
-- Ads tracking (crm_ad_*) is DEFERRED — not in this migration.

CREATE TABLE IF NOT EXISTS crm_segment (
  segment_id    TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  description   TEXT,
  is_dynamic    INTEGER NOT NULL DEFAULT 1,  -- 1=dynamic(rule-based), 0=static(manual-only)
  definition    TEXT,                         -- JSON rule: {"value_group":["VIP"],"customer_status":"at_risk",...}
  owner_user_id TEXT REFERENCES crm_app_user(user_id),
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS trg_segment_touch
AFTER UPDATE ON crm_segment
BEGIN
  UPDATE crm_segment
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

CREATE TABLE IF NOT EXISTS crm_segment_member (
  segment_id TEXT NOT NULL REFERENCES crm_segment(segment_id),
  party_id   TEXT NOT NULL REFERENCES crm_party(party_id),
  source     TEXT NOT NULL DEFAULT 'rule' CHECK (source IN ('rule', 'manual')),
  added_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (segment_id, party_id)
);

CREATE INDEX IF NOT EXISTS idx_segment_member_party
  ON crm_segment_member (party_id);

CREATE TABLE IF NOT EXISTS crm_campaign (
  campaign_id  TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  objective    TEXT NOT NULL CHECK (objective IN ('reactivation', 'winback', 'upsell', 'crosssell')),
  channel      TEXT,
  segment_id   TEXT REFERENCES crm_segment(segment_id),
  status       TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'done')),
  scheduled_at TEXT,
  created_by   TEXT REFERENCES crm_app_user(user_id),
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS trg_campaign_touch
AFTER UPDATE ON crm_campaign
BEGIN
  UPDATE crm_campaign
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

CREATE INDEX IF NOT EXISTS idx_campaign_segment
  ON crm_campaign (segment_id);

CREATE TABLE IF NOT EXISTS crm_campaign_target (
  campaign_id            TEXT NOT NULL REFERENCES crm_campaign(campaign_id),
  party_id               TEXT NOT NULL REFERENCES crm_party(party_id),
  status                 TEXT NOT NULL DEFAULT 'queued'
                         CHECK (status IN ('queued', 'sent', 'responded', 'converted', 'skipped')),
  assigned_user_id       TEXT REFERENCES crm_app_user(user_id),
  last_touch_at          TEXT,
  converted_order_code   TEXT,
  converted_revenue_vnd  INTEGER,
  converted_at           TEXT,
  PRIMARY KEY (campaign_id, party_id)
);

CREATE INDEX IF NOT EXISTS idx_campaign_target_assignee_status
  ON crm_campaign_target (assigned_user_id, status);

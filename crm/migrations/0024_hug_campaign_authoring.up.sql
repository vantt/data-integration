-- Migration 0024 UP: crm_hug_campaign + crm_hug_campaign_history
--
-- crm_hug_campaign is the local authoring source of truth for Hug routing rules.
-- Columns mirror the edge hug_campaign table (schema_hug.sql) exactly, plus
-- created_at and WITHOUT quota_used (edge-only counter; not tracked locally).
-- Rules are pushed to the Worker's D1 via campaign_push.py after each save.
--
-- crm_hug_campaign_history is an append-only snapshot table.
-- A full JSON snapshot of each row is written on every create or update,
-- enabling rollback to any prior state without a separate diff/audit table.
-- No FK to crm_hug_campaign so history survives a deleted campaign row.

CREATE TABLE IF NOT EXISTS crm_hug_campaign (
    campaign_id      TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    -- targeting JSON object: keys ANDed, list values ORed within each key.
    -- '{}' means DEFAULT (always matches any scan).
    targeting        TEXT NOT NULL DEFAULT '{}',
    destination_type TEXT NOT NULL CHECK (destination_type IN ('zalo_oa', 'cf_pages', 'url')),
    destination_url  TEXT NOT NULL,
    offer_ref        TEXT,                          -- voucher/campaign code; NULL = no offer
    priority         INTEGER NOT NULL DEFAULT 100,  -- lower number = higher priority
    schedule_start   TEXT,                          -- ISO-8601 UTC; NULL = no start constraint
    schedule_end     TEXT,                          -- ISO-8601 UTC; NULL = no end constraint
    quota_total      INTEGER,                       -- NULL = unlimited
    status           TEXT NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active', 'paused', 'archived')),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Composite index mirrors edge query pattern: filter active, sort by priority
CREATE INDEX IF NOT EXISTS idx_crm_hug_campaign_status_priority
    ON crm_hug_campaign (status, priority);

-- Append-only snapshot for versioning and rollback support.
-- snapshot holds the full crm_hug_campaign row as JSON at the moment of save.
CREATE TABLE IF NOT EXISTS crm_hug_campaign_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    snapshot    TEXT NOT NULL,  -- JSON of full crm_hug_campaign row at save time
    saved_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Index supports list_history(campaign_id, limit=N) ordered by newest first
CREATE INDEX IF NOT EXISTS idx_crm_hug_campaign_history_lookup
    ON crm_hug_campaign_history (campaign_id, saved_at DESC);

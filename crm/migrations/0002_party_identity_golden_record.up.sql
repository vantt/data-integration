-- Migration 0002 UP: party, party_identity, dedup_candidate, party_merge_log + FTS5
-- SQLite dialect — TEXT uuid (app-generated), TEXT UTC ISO-8601, INTEGER bool, crm_* prefix

-- Core golden-record table
CREATE TABLE IF NOT EXISTS crm_party (
  party_id      TEXT PRIMARY KEY,
  party_type    TEXT NOT NULL DEFAULT 'person',     -- person|org
  display_name  TEXT,
  primary_phone TEXT,                               -- normalised E.164-ish (+84...)
  primary_email TEXT,
  status        TEXT NOT NULL DEFAULT 'active',     -- active|inactive|blocked
  is_merged     INTEGER NOT NULL DEFAULT 0,         -- 1 if absorbed into another party
  merged_into   TEXT REFERENCES crm_party(party_id),
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS trg_party_touch
AFTER UPDATE ON crm_party
BEGIN
  UPDATE crm_party
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

-- Identity → party mapping (dedup mechanism)
-- UNIQUE(identity_type, identity_value) enforces: one phone/email belongs to exactly one party
CREATE TABLE IF NOT EXISTS crm_party_identity (
  identity_id    TEXT PRIMARY KEY,
  party_id       TEXT NOT NULL REFERENCES crm_party(party_id),
  source_system  TEXT NOT NULL,   -- sapo_v2|messenger|zalo|manual
  identity_type  TEXT NOT NULL,   -- sapo_customer|phone|email|psid|zalo_uid|customer_code
  identity_value TEXT NOT NULL,   -- normalised value
  confidence     REAL NOT NULL DEFAULT 1.0,
  is_primary     INTEGER NOT NULL DEFAULT 0,
  verified_at    TEXT,
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (identity_type, identity_value)
);

-- Suspect-match queue for manual review
CREATE TABLE IF NOT EXISTS crm_dedup_candidate (
  candidate_id TEXT PRIMARY KEY,
  party_a      TEXT NOT NULL REFERENCES crm_party(party_id),
  party_b      TEXT NOT NULL REFERENCES crm_party(party_id),
  match_rule   TEXT NOT NULL,   -- exact_phone|exact_email|fts_name_phone
  match_score  REAL NOT NULL,
  status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','merged','rejected')),
  reviewed_by  TEXT REFERENCES crm_app_user(user_id),
  reviewed_at  TEXT,
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Reversible merge audit log
CREATE TABLE IF NOT EXISTS crm_party_merge_log (
  merge_id           TEXT PRIMARY KEY,
  surviving_party_id TEXT NOT NULL REFERENCES crm_party(party_id),
  merged_party_id    TEXT NOT NULL,   -- soft ref — party may be is_merged after this
  reason             TEXT,
  merged_by          TEXT REFERENCES crm_app_user(user_id),
  snapshot           TEXT,            -- JSON: pre-merge state for undo
  merged_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  undone_at          TEXT             -- set when UndoMerge is applied; prevents double-undo
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_party_phone
  ON crm_party (primary_phone);

CREATE INDEX IF NOT EXISTS idx_identity_value
  ON crm_party_identity (identity_type, identity_value);

CREATE INDEX IF NOT EXISTS idx_dedup_status
  ON crm_dedup_candidate (status);

-- FTS5 virtual table for fuzzy name search (unicode61 with diacritics removal)
-- Kept in sync with crm_party via triggers
CREATE VIRTUAL TABLE IF NOT EXISTS crm_party_fts
  USING fts5(party_id UNINDEXED, name_norm, tokenize='unicode61 remove_diacritics 2');

-- Populate FTS from existing rows (none at migration time, but future-safe)
INSERT OR IGNORE INTO crm_party_fts (party_id, name_norm)
SELECT party_id, lower(display_name) FROM crm_party WHERE display_name IS NOT NULL;

-- Keep FTS in sync: insert
CREATE TRIGGER IF NOT EXISTS trg_party_fts_insert
AFTER INSERT ON crm_party
WHEN NEW.display_name IS NOT NULL
BEGIN
  INSERT OR IGNORE INTO crm_party_fts (party_id, name_norm)
  VALUES (NEW.party_id, lower(NEW.display_name));
END;

-- Keep FTS in sync: update (NULL guard — skip insert when display_name is NULL)
CREATE TRIGGER IF NOT EXISTS trg_party_fts_update
AFTER UPDATE OF display_name ON crm_party
BEGIN
  DELETE FROM crm_party_fts WHERE party_id = OLD.party_id;
  INSERT INTO crm_party_fts (party_id, name_norm)
  SELECT NEW.party_id, lower(NEW.display_name) WHERE NEW.display_name IS NOT NULL;
END;

-- Keep FTS in sync: delete
CREATE TRIGGER IF NOT EXISTS trg_party_fts_delete
AFTER DELETE ON crm_party
BEGIN
  DELETE FROM crm_party_fts WHERE party_id = OLD.party_id;
END;

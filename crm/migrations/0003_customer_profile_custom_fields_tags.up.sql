-- Migration 0003 UP: customer_profile, custom_field_def, tag, party_tag, note + view crm_party_360
-- SQLite dialect — TEXT uuid (app-generated), TEXT UTC ISO-8601, INTEGER bool, crm_* prefix

-- 1-1 enrichment profile per party (owner = assigned sales rep)
CREATE TABLE IF NOT EXISTS crm_customer_profile (
  party_id         TEXT PRIMARY KEY REFERENCES crm_party(party_id),
  owner_user_id    TEXT REFERENCES crm_app_user(user_id),
  lifecycle_stage  TEXT,               -- lead|new|active|at_risk|churned (manual, supplements warehouse cache)
  acquisition_source TEXT,             -- confirmed source as recorded by sales rep
  birthday         TEXT,               -- ISO-8601 date YYYY-MM-DD
  address          TEXT,               -- JSON {province,district,ward,street}
  preferences      TEXT,               -- JSON: manually recorded preferences/behaviours
  custom           TEXT NOT NULL DEFAULT '{}',  -- JSON map of custom field values (key ↔ crm_custom_field_def.field_key)
  consent_contact  INTEGER NOT NULL DEFAULT 1,  -- 1=consented, 0=opted-out (compliance gate for Phase 06 campaigns)
  created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS trg_customer_profile_touch
AFTER UPDATE ON crm_customer_profile
BEGIN
  UPDATE crm_customer_profile
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

CREATE INDEX IF NOT EXISTS idx_profile_owner
  ON crm_customer_profile (owner_user_id);

-- Registry of dynamic custom fields — adding a new field requires no schema migration.
-- App validates custom JSON values against this registry (data_type, is_required, options).
CREATE TABLE IF NOT EXISTS crm_custom_field_def (
  field_id    TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL DEFAULT 'party',   -- party|order (extensible)
  field_key   TEXT NOT NULL,                   -- key inside custom JSON blob
  label       TEXT NOT NULL,
  data_type   TEXT NOT NULL CHECK (data_type IN ('text','number','date','bool','select','multiselect')),
  options     TEXT,                            -- JSON array of allowed values for select/multiselect
  is_required INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 1,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  UNIQUE (entity_type, field_key)
);

-- Tags with optional category grouping and display colour.
CREATE TABLE IF NOT EXISTS crm_tag (
  tag_id   TEXT PRIMARY KEY,
  name     TEXT NOT NULL,
  category TEXT,
  color    TEXT,
  UNIQUE (category, name)
);

-- Many-to-many party ↔ tag with audit (who tagged, when).
CREATE TABLE IF NOT EXISTS crm_party_tag (
  party_id  TEXT NOT NULL REFERENCES crm_party(party_id),
  tag_id    TEXT NOT NULL REFERENCES crm_tag(tag_id),
  tagged_by TEXT REFERENCES crm_app_user(user_id),
  tagged_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (party_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_party_tag_tag
  ON crm_party_tag (tag_id);

-- Free-form notes on a party with author attribution.
CREATE TABLE IF NOT EXISTS crm_note (
  note_id        TEXT PRIMARY KEY,
  party_id       TEXT NOT NULL REFERENCES crm_party(party_id),
  body           TEXT NOT NULL,
  author_user_id TEXT REFERENCES crm_app_user(user_id),
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_note_party_created
  ON crm_note (party_id, created_at);

-- Seed starter custom field definitions (idempotent).
INSERT OR IGNORE INTO crm_custom_field_def (field_id, entity_type, field_key, label, data_type, options, is_required, is_active, sort_order)
VALUES
  ('cfd-00000000-0001', 'party', 'skin_type',        'Loại da',           'select',      '["dầu","khô","hỗn hợp","nhạy cảm","thường"]', 0, 1, 10),
  ('cfd-00000000-0002', 'party', 'loyal_tier',       'Hạng thành viên',   'select',      '["bronze","silver","gold","platinum"]',         0, 1, 20),
  ('cfd-00000000-0003', 'party', 'preferred_contact','Kênh liên hệ ưu tiên','select',    '["phone","zalo","messenger","email"]',           0, 1, 30),
  ('cfd-00000000-0004', 'party', 'note_internal',    'Ghi chú nội bộ',    'text',        NULL,                                             0, 1, 40);

-- Seed starter tag categories (idempotent).
INSERT OR IGNORE INTO crm_tag (tag_id, name, category, color)
VALUES
  ('tag-00000000-0001', 'VIP',           'segment',  '#FFD700'),
  ('tag-00000000-0002', 'Da nhạy cảm',   'profile',  '#FF6B6B'),
  ('tag-00000000-0003', 'Khách quen',     'segment',  '#4ECDC4'),
  ('tag-00000000-0004', 'Cần follow-up',  'action',   '#FFA500'),
  ('tag-00000000-0005', 'Tiềm năng',      'segment',  '#95E1D3');

-- View crm_party_360: single-query profile for the party detail screen.
-- Joins crm_party + crm_customer_profile (LEFT JOIN — no profile yet is fine) + aggregated tags.
-- Phase 04 extends this view with cache.wh_customer_insight + action_queue + wh_order_hdr.
-- NOTE: deliberately omits cache.* tables — cache.db is empty until Phase 04 populates it;
--       referencing cache.wh_customer_insight here would break this view right now.
CREATE VIEW IF NOT EXISTS crm_party_360 AS
SELECT
  p.party_id,
  p.party_type,
  p.display_name,
  p.primary_phone,
  p.primary_email,
  p.status,
  p.is_merged,
  p.created_at            AS party_created_at,
  p.updated_at            AS party_updated_at,
  -- profile fields (NULL when no profile row exists yet)
  cp.owner_user_id,
  cp.lifecycle_stage,
  cp.acquisition_source,
  cp.birthday,
  cp.address,
  cp.preferences,
  cp.custom,
  cp.consent_contact,
  cp.updated_at           AS profile_updated_at,
  -- aggregated tags as JSON array [{tag_id,name,category,color}]; COALESCE returns '[]' for untagged parties.
  COALESCE(
    (
      SELECT json_group_array(
        json_object('tag_id', t.tag_id, 'name', t.name, 'category', t.category, 'color', t.color)
      )
      FROM crm_party_tag pt
      JOIN crm_tag t ON t.tag_id = pt.tag_id
      WHERE pt.party_id = p.party_id
    ),
    '[]'
  ) AS tags_json
FROM crm_party p
LEFT JOIN crm_customer_profile cp ON cp.party_id = p.party_id
WHERE p.is_merged = 0;

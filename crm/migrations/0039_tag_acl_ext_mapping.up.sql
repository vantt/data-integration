-- Migration 0039 UP: tag Anti-Corruption Layer (ACL) — decouple CRM canonical tags
-- from any specific sales platform's vocabulary (Sapo, Haravan, Shopify, ...).
-- Follows the same ACL pattern as crm_party_external_id (migration 0009).
--
-- crm_ext_tag: registry of external-system tag/group values. ext_key is the
-- STABLE key of the external system (Sapo: customer_group id as string, e.g.
-- '1812239' — NOT the group code, which Sapo renames on the same id).
--
-- crm_ext_tag_map: N:M mapping ext_tag -> crm_tag. One ext_tag can fan out to
-- multiple crm_tag (e.g. Sapo group WHOLESALE -> tag "KH Si" + tag "B2B"); one
-- crm_tag can receive from multiple ext_tag. UNIQUE (ext_tag_id, crm_tag_id) is
-- required so a later governance repoint (plan 260706-0833) can upsert this
-- mapping idempotently instead of accumulating duplicate rows.
CREATE TABLE IF NOT EXISTS crm_ext_tag (
  ext_tag_id    TEXT PRIMARY KEY,
  source_system TEXT NOT NULL,   -- 'sapo_v2' | 'haravan' | 'shopify'
  ext_key       TEXT NOT NULL,   -- stable external key (Sapo: customer_group id, e.g. '1812239')
  ext_label     TEXT,            -- display label for admins (name/code as seen in source system)
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (source_system, ext_key)
);

CREATE TABLE IF NOT EXISTS crm_ext_tag_map (
  map_id     TEXT PRIMARY KEY,
  ext_tag_id TEXT NOT NULL REFERENCES crm_ext_tag(ext_tag_id),
  crm_tag_id TEXT NOT NULL REFERENCES crm_tag(tag_id),
  direction  TEXT NOT NULL DEFAULT 'inbound',   -- 'inbound' | 'outbound' | 'both'
  priority   INTEGER NOT NULL DEFAULT 0,        -- tie-break when a party has multiple ext_tag mapping into the same category
  is_active  INTEGER NOT NULL DEFAULT 1,        -- 1=active mapping, 0=disabled (e.g. RETAIL seeded inactive)
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (ext_tag_id, crm_tag_id)
);

CREATE INDEX IF NOT EXISTS idx_ext_tag_map_active
  ON crm_ext_tag_map (ext_tag_id, is_active);

-- Extend crm_party_tag with sync provenance so app logic can tell a CRM-user
-- assigned tag ('crm_user', immutable by sync) apart from a tag mirrored in
-- from an external system ('sapo_v2_sync', ...). Existing rows backfill to
-- 'crm_user' via the DEFAULT — they were all assigned manually pre-ACL.
ALTER TABLE crm_party_tag ADD COLUMN source TEXT NOT NULL DEFAULT 'crm_user';
ALTER TABLE crm_party_tag ADD COLUMN ext_ref TEXT;   -- original ext_key (e.g. Sapo group id) for tracing/audit

CREATE INDEX IF NOT EXISTS idx_party_tag_source_party
  ON crm_party_tag (source, party_id);

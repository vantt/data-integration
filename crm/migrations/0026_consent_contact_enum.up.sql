-- Migration 0026 UP: consent_contact enum support
-- Adds consent_enum TEXT column (NULL=na/not-collected | 'allowed' | 'denied').
-- The old consent_contact INTEGER column stays (compatibility); view aliases consent_enum.
-- All existing rows start as NULL (na) — prior DEFAULT 1 was never real collected data.
--
-- Recovery block: if crm_customer_profile was dropped by a failed prior migration attempt
-- (abandoned DROP+RENAME sequence), CREATE TABLE IF NOT EXISTS recreates it with the correct
-- schema including consent_enum. When the table already exists this is a no-op.

CREATE TABLE IF NOT EXISTS crm_customer_profile (
  party_id           TEXT PRIMARY KEY REFERENCES crm_party(party_id),
  owner_user_id      TEXT REFERENCES crm_app_user(user_id),
  lifecycle_stage    TEXT,
  acquisition_source TEXT,
  birthday           TEXT,
  address            TEXT,
  preferences        TEXT,
  custom             TEXT NOT NULL DEFAULT '{}',
  consent_contact    INTEGER NOT NULL DEFAULT 1,
  created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  gender             TEXT,
  consent_enum       TEXT DEFAULT NULL
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

-- Add consent_enum to tables that existed before this migration.
-- The migration runner ignores "duplicate column name" errors, so this is idempotent:
-- if the table was just created above (consent_enum already present), this is a safe no-op.
ALTER TABLE crm_customer_profile ADD COLUMN consent_enum TEXT DEFAULT NULL;

-- Rebuild view (based on 0017) to expose consent_enum as consent_contact
DROP VIEW IF EXISTS crm_party_360;
CREATE VIEW crm_party_360 AS
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
  cp.owner_user_id,
  cp.lifecycle_stage,
  cp.acquisition_source,
  cp.birthday,
  cp.gender,
  cp.address,
  cp.preferences,
  cp.custom,
  cp.consent_enum         AS consent_contact,
  cp.updated_at           AS profile_updated_at,
  p.address_line,
  p.ward,
  p.district,
  p.province,
  p.address_source,
  p.address_note,
  COALESCE(
    (
      SELECT json_group_array(
        json_object('tag_id', t.tag_id, 'name', t.name, 'display_label', t.display_label,
                    'category', t.category, 'color', t.color)
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

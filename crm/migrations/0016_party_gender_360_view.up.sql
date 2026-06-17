-- Migration 0016 UP: gender field on crm_customer_profile; rebuild crm_party_360 view
-- to include crm_party.address_* columns (omitted from 0003) and new gender column.

ALTER TABLE crm_customer_profile ADD COLUMN gender TEXT;
  -- male | female | other | unknown — nullable; NULL means not collected

-- Rebuild view to expose address columns (crm_party.address_*) and gender (crm_customer_profile.gender).
-- crm_party_360 was created in 0003 without address fields; DROP + CREATE is the SQLite way to alter a view.
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
  -- profile fields (NULL when no profile row exists yet)
  cp.owner_user_id,
  cp.lifecycle_stage,
  cp.acquisition_source,
  cp.birthday,
  cp.gender,
  cp.address,
  cp.preferences,
  cp.custom,
  cp.consent_contact,
  cp.updated_at           AS profile_updated_at,
  -- address fields (crm_party migration 0007 — absent from 0003 view)
  p.address_line,
  p.ward,
  p.district,
  p.province,
  p.address_source,
  p.address_note,
  -- aggregated tags as JSON array [{tag_id,name,category,color}]
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

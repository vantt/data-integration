-- Migration 0017 UP: add display_label to crm_tag for human-readable label separate from slug
-- display_label: shown in UI chips/dropdowns; name (slug) stays machine-readable
-- Backfill: existing tags use their name as initial display_label

ALTER TABLE crm_tag ADD COLUMN display_label TEXT;

UPDATE crm_tag SET display_label = name WHERE display_label IS NULL OR display_label = '';

-- Rebuild crm_party_360 to include display_label in tags_json
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
  cp.consent_contact,
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

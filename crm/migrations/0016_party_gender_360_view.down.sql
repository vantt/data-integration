-- Migration 0016 DOWN: restore crm_party_360 to pre-0016 shape; drop gender column.
-- SQLite has no DROP COLUMN before 3.35; we recreate crm_customer_profile instead.
-- WARNING: destructive — only use in dev; production rollback should be handled manually.

DROP VIEW IF EXISTS crm_party_360;

-- Restore view without gender and without address columns (0003 shape)
CREATE VIEW crm_party_360 AS
SELECT
  p.party_id, p.party_type, p.display_name, p.primary_phone, p.primary_email,
  p.status, p.is_merged,
  p.created_at AS party_created_at, p.updated_at AS party_updated_at,
  cp.owner_user_id, cp.lifecycle_stage, cp.acquisition_source, cp.birthday,
  cp.address, cp.preferences, cp.custom, cp.consent_contact,
  cp.updated_at AS profile_updated_at,
  COALESCE(
    (SELECT json_group_array(json_object('tag_id',t.tag_id,'name',t.name,'category',t.category,'color',t.color))
     FROM crm_party_tag pt JOIN crm_tag t ON t.tag_id=pt.tag_id WHERE pt.party_id=p.party_id),
    '[]'
  ) AS tags_json
FROM crm_party p
LEFT JOIN crm_customer_profile cp ON cp.party_id = p.party_id
WHERE p.is_merged = 0;

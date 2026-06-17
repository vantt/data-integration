-- Migration 0014 UP: custom field section grouping + tag category enum migration
-- section: free-text grouping label rendered as sub-headers in M06 / M13
-- tag categories migrated from old free-form values to the new enum:
--   behavioral | demographic | preference | vip_tier | risk | source

ALTER TABLE crm_custom_field_def ADD COLUMN section TEXT;

-- Backfill sections for seed definitions
UPDATE crm_custom_field_def SET section = 'Hồ sơ khách hàng' WHERE field_key = 'skin_type';
UPDATE crm_custom_field_def SET section = 'Phân tầng'         WHERE field_key = 'loyal_tier';
UPDATE crm_custom_field_def SET section = 'Hồ sơ khách hàng' WHERE field_key = 'preferred_contact';
UPDATE crm_custom_field_def SET section = 'Nội bộ'            WHERE field_key = 'note_internal';

-- Migrate seed tag categories to enum values
UPDATE crm_tag SET category = 'vip_tier'   WHERE tag_id = 'tag-00000000-0001';  -- VIP
UPDATE crm_tag SET category = 'preference' WHERE tag_id = 'tag-00000000-0002';  -- Da nhạy cảm
UPDATE crm_tag SET category = 'behavioral' WHERE tag_id = 'tag-00000000-0003';  -- Khách quen
UPDATE crm_tag SET category = 'risk'       WHERE tag_id = 'tag-00000000-0004';  -- Cần follow-up
UPDATE crm_tag SET category = 'vip_tier'   WHERE tag_id = 'tag-00000000-0005';  -- Tiềm năng

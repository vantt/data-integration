-- Migration 0003 DOWN: drop all objects created in 0003 UP (reverse order)
DROP VIEW    IF EXISTS crm_party_360;
DROP TABLE   IF EXISTS crm_note;
DROP TABLE   IF EXISTS crm_party_tag;
DROP TABLE   IF EXISTS crm_tag;
DROP TABLE   IF EXISTS crm_custom_field_def;
DROP TRIGGER IF EXISTS trg_customer_profile_touch;
DROP TABLE   IF EXISTS crm_customer_profile;

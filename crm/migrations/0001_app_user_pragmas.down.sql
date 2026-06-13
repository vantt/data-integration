-- Migration 0001 DOWN: drop trigger and crm_app_user table

DROP TRIGGER IF EXISTS trg_app_user_touch;
DROP TABLE IF EXISTS crm_app_user;

-- Migration 0030 DOWN: remove uniqueness constraint on staff_id
DROP INDEX IF EXISTS uidx_app_user_staff_id;

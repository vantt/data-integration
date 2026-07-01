-- Add staff_user_id to crm_last_contact so Band-4 "Đã Liên Hệ" rows can
-- display who made the contact without requiring a join at render time.
ALTER TABLE crm_last_contact ADD COLUMN staff_user_id TEXT REFERENCES crm_app_user(user_id);

-- Backfill from crm_activity_log for existing rows.
UPDATE crm_last_contact
SET staff_user_id = (
    SELECT al.staff_user_id
    FROM crm_activity_log al
    WHERE al.activity_id = crm_last_contact.last_activity_id
    LIMIT 1
)
WHERE staff_user_id IS NULL;

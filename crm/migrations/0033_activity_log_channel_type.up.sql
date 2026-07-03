-- Migration 0033 UP: add channel_type to crm_activity_log
-- `channel` holds the raw contact value (phone number, Zalo handle, ...);
-- `channel_type` holds which channel it is (call|zalo|fb|email|visit|other) so the
-- UI can label the value correctly (e.g. "Zalo: <handle>" vs "Điện thoại: <số>").
ALTER TABLE crm_activity_log ADD COLUMN channel_type TEXT;

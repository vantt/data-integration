-- Migration 0044 UP: nối tag về đúng activity log entry (cuộc gọi) đã sinh ra nó.
-- Nullable — NULL hợp lệ khi tag gắn ngoài luồng Log Activity (M03 modal, sync,
-- governance normalize, ...). REFERENCES crm_activity_log(activity_id), theo
-- đúng convention của migration 0019 (crm_note.source_activity_id).
ALTER TABLE crm_party_tag ADD COLUMN source_activity_id TEXT REFERENCES crm_activity_log(activity_id);
CREATE INDEX IF NOT EXISTS idx_party_tag_source_activity ON crm_party_tag(source_activity_id);

-- Migration 0041 UP: crm_tag provisional/archived flags + seed 8 health domain tags
-- Part of plan 260706-0833-crm-health-profile-tag-governance (Phase 01 — schema layer only).
--
-- is_provisional: 0=canonical (shown in pickers/chips), 1=awaiting admin review.
--   Level 1 provisional: category set + is_provisional=1 (domain known, tag unvalidated).
--   Level 2 provisional: category IS NULL + is_provisional=1 (domain unknown, text only).
-- is_archived: 0=active, 1=retired — hidden from pickers, crm_party_tag history preserved.
--
-- crm_tag.category has no CHECK constraint (free-form TEXT), so no ALTER needed there.
ALTER TABLE crm_tag ADD COLUMN is_provisional INTEGER NOT NULL DEFAULT 0;
ALTER TABLE crm_tag ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0;

-- Seed canonical health domain tags consumed by S14 call cockpit collect region (Phase 02).
INSERT OR IGNORE INTO crm_tag (tag_id, name, category, color, display_label, is_provisional, is_archived) VALUES
  ('tag-health-0001', 'tim-mach',      'health_domain', '#E53E3E', 'Tim mạch',            0, 0),
  ('tag-health-0002', 'ho-hap',        'health_domain', '#3182CE', 'Hô hấp',              0, 0),
  ('tag-health-0003', 'mien-dich',     'health_domain', '#38A169', 'Miễn dịch',           0, 0),
  ('tag-health-0004', 'xuong-khop',    'health_domain', '#DD6B20', 'Xương khớp',          0, 0),
  ('tag-health-0005', 'tieu-hoa',      'health_domain', '#D69E2E', 'Tiêu hóa',            0, 0),
  ('tag-health-0006', 'than-kinh-ngu', 'health_domain', '#805AD5', 'Thần kinh & giấc ngủ', 0, 0),
  ('tag-health-0007', 'nang-luong',    'health_domain', '#319795', 'Năng lượng',          0, 0),
  ('tag-health-0008', 'da',            'health_domain', '#D53F8C', 'Da',                  0, 0);

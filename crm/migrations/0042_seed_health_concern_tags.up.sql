-- Migration 0042 UP: seed common health_concern canonical tags.
-- Part of plan 260706-0833-crm-health-profile-tag-governance follow-up
-- (chip-select coverage for the long-tail health_concern category, reducing
-- how often reps need the free-text tag-creation path added alongside this).
--
-- category='health_concern', is_provisional=0 (canonical — curated, not
-- awaiting admin review). Rep-created concerns not in this list still flow
-- through the provisional (L1) path and land in the Tag Governance L1 queue.
INSERT OR IGNORE INTO crm_tag (tag_id, name, category, color, display_label, is_provisional, is_archived) VALUES
  ('tag-health-0009', 'huyet-ap-cao',  'health_concern', '#E53E3E', 'Huyết áp cao',       0, 0),
  ('tag-health-0010', 'mo-mau-cao',    'health_concern', '#E53E3E', 'Mỡ máu cao',         0, 0),
  ('tag-health-0011', 'mat-ngu',       'health_concern', '#805AD5', 'Mất ngủ',            0, 0),
  ('tag-health-0012', 'cang-thang',    'health_concern', '#805AD5', 'Căng thẳng / stress', 0, 0),
  ('tag-health-0013', 'dau-khop',      'health_concern', '#DD6B20', 'Đau khớp',           0, 0),
  ('tag-health-0014', 'tieu-hoa-kem',  'health_concern', '#D69E2E', 'Tiêu hóa kém',       0, 0),
  ('tag-health-0015', 'di-ung',        'health_concern', '#38A169', 'Dị ứng',             0, 0),
  ('tag-health-0016', 'met-moi',       'health_concern', '#319795', 'Mệt mỏi / thiếu năng lượng', 0, 0);

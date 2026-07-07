-- Migration 0042 DOWN: remove seeded health_concern tags.
DELETE FROM crm_tag WHERE tag_id IN (
  'tag-health-0009', 'tag-health-0010', 'tag-health-0011', 'tag-health-0012',
  'tag-health-0013', 'tag-health-0014', 'tag-health-0015', 'tag-health-0016'
);

-- Migration 0041 DOWN: remove seeded health domain tags + drop provisional/archived flags.
-- SQLite 3.46 (in-use version) supports DROP COLUMN directly — same approach as
-- migrations 0035 (crm_activity_log.outcome_reason) and 0039 (crm_party_tag.source/ext_ref).
DELETE FROM crm_tag WHERE tag_id IN (
  'tag-health-0001', 'tag-health-0002', 'tag-health-0003', 'tag-health-0004',
  'tag-health-0005', 'tag-health-0006', 'tag-health-0007', 'tag-health-0008'
);

ALTER TABLE crm_tag DROP COLUMN is_archived;
ALTER TABLE crm_tag DROP COLUMN is_provisional;

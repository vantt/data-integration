-- Migration 0040 DOWN: remove seeded Sapo tag mapping rows by fixed id (idempotent).
-- Does NOT touch 'tag-00000000-0001' (VIP) — pre-existing seed from migration 0003,
-- not owned by this migration.
DELETE FROM crm_ext_tag_map WHERE map_id IN (
  'extmap-sapo_v2-1812239',
  'extmap-sapo_v2-2421894',
  'extmap-sapo_v2-2308212',
  'extmap-sapo_v2-2281219',
  'extmap-sapo_v2-1812240'
);

DELETE FROM crm_ext_tag WHERE ext_tag_id IN (
  'exttag-sapo_v2-1812238',
  'exttag-sapo_v2-1812239',
  'exttag-sapo_v2-2421894',
  'exttag-sapo_v2-2308212',
  'exttag-sapo_v2-2281219',
  'exttag-sapo_v2-1812240'
);

DELETE FROM crm_tag WHERE tag_id IN (
  'tag-00000000-0006',
  'tag-00000000-0007',
  'tag-00000000-0008',
  'tag-00000000-0009'
);

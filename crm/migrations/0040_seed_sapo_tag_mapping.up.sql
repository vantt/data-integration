-- Migration 0040 UP: seed crm_ext_tag / crm_ext_tag_map with the 6 verified Sapo
-- customer_group ids (ext_key = group id, stable across Sapo's code renames —
-- see migration 0039 header + plan 260619-0830-crm-tag-acl-sync phase-02).
--
-- Re-verified 2026-07-07 against main_marts.dim_customers (post phase-00 staging
-- fix): exactly 6 real groups, same set as the phase doc's table —
--   1812238 RETAIL (TYPE_RETAIL/BANLE, 6528+123=6651 rows)
--   1812239 WHOLESALE (TYPE_WHOLESALE/BANBUON, 159+2=161 rows)
--   2421894 US (CTN00014, 662 rows)
--   2308212 Selly (CTN00013, 104 rows)
--   2281219 Ky Gui (KY_GUI, 11 rows)
--   1812240 VIP (VIP, 1 row)
-- No new group id appeared. Counts drifted slightly from the plan's snapshot
-- (natural customer growth) but group set is identical — no business decision
-- needed here.
--
-- This is a pure data migration (INSERT OR IGNORE only, no DDL).
--
-- Category discipline (see phase-02 Key Insights): the 4 new tags use
-- 'demographic' or 'source' — NEVER 'vip_tier'/'risk'. Those two categories are
-- consumed by mart_customer_action_queue (plan 260706-1738), which only trusts
-- tags with source='crm_user'; keeping sync-owned tags out of those categories
-- is defense-in-depth against accidental semantic collision. VIP is the sole
-- exception: it maps into the pre-existing seed tag 'tag-00000000-0001'
-- (category 'vip_tier', set by migration 0014) which already carries only 1
-- customer and plan 260706-1738 already filters by source — safe.
--
-- RETAIL (1812238) is the Sapo default group: 6.4k+/7.5k customers, zero
-- discriminating information. Per phase doc's mapping table (crm_tag column
-- explicitly "-", i.e. none), it gets a crm_ext_tag entry so sync recognizes
-- the group id as known (no "skipped-no-mapping" log noise), but deliberately
-- NO crm_ext_tag_map row and NO crm_tag — there is nothing meaningful to map
-- it to. This keeps `SELECT count(*) FROM crm_ext_tag_map WHERE is_active=1`
-- at exactly 5 without an inactive placeholder row pointing at a fabricated
-- tag. Reactivating RETAIL later (if ever needed) is a follow-up INSERT, not
-- a migration or schema change.

-- 1. Four new canonical tags (deterministic seed ids, continuing the
--    tag-00000000-000N sequence started in migration 0003).
INSERT OR IGNORE INTO crm_tag (tag_id, name, category, color)
VALUES
  ('tag-00000000-0006', 'KH Sỉ',          'demographic', '#8E44AD'),
  ('tag-00000000-0007', 'KH US giao hộ',  'demographic', '#3498DB'),
  ('tag-00000000-0008', 'Selly',          'source',       '#16A085'),
  ('tag-00000000-0009', 'Ký Gửi',         'demographic', '#E67E22');

-- 2. Registry of all 6 verified Sapo customer_group ids (ext_key = group id as
--    TEXT — never let this get coerced to INTEGER, see migration 0039 note).
INSERT OR IGNORE INTO crm_ext_tag (ext_tag_id, source_system, ext_key, ext_label)
VALUES
  ('exttag-sapo_v2-1812238', 'sapo_v2', '1812238', 'RETAIL (BANLE/TYPE_RETAIL) - default group, zero info'),
  ('exttag-sapo_v2-1812239', 'sapo_v2', '1812239', 'WHOLESALE (BANBUON/TYPE_WHOLESALE)'),
  ('exttag-sapo_v2-2421894', 'sapo_v2', '2421894', 'US (CTN00014)'),
  ('exttag-sapo_v2-2308212', 'sapo_v2', '2308212', 'Selly (CTN00013)'),
  ('exttag-sapo_v2-2281219', 'sapo_v2', '2281219', 'Ky Gui (KY_GUI)'),
  ('exttag-sapo_v2-1812240', 'sapo_v2', '1812240', 'VIP');

-- 3. Active mappings — exactly 5 (RETAIL intentionally excluded, see header).
INSERT OR IGNORE INTO crm_ext_tag_map (map_id, ext_tag_id, crm_tag_id, direction, is_active)
VALUES
  ('extmap-sapo_v2-1812239', 'exttag-sapo_v2-1812239', 'tag-00000000-0006', 'inbound', 1),
  ('extmap-sapo_v2-2421894', 'exttag-sapo_v2-2421894', 'tag-00000000-0007', 'inbound', 1),
  ('extmap-sapo_v2-2308212', 'exttag-sapo_v2-2308212', 'tag-00000000-0008', 'inbound', 1),
  ('extmap-sapo_v2-2281219', 'exttag-sapo_v2-2281219', 'tag-00000000-0009', 'inbound', 1),
  ('extmap-sapo_v2-1812240', 'exttag-sapo_v2-1812240', 'tag-00000000-0001', 'inbound', 1);

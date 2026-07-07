# Phase 02 Implementation Report — Seed Sapo Tag Mapping

**Plan:** `plans/260619-0830-crm-tag-acl-sync/` · **Phase:** phase-02-seed-sapo-mapping.md
**Status:** DONE

## Step 1 — re-verify query (mandatory, before writing migration)

Ran against `main_marts.dim_customers` in `olap.duckdb` (via `data_platform` container, read_only):

```sql
SELECT customer_group_id, customer_group_name, customer_group_code, COUNT(*)
FROM main_marts.dim_customers
WHERE customer_group_id IS NOT NULL
GROUP BY 1, 2, 3 ORDER BY 4 DESC;
```

Result:
```
1812238  RETAIL      TYPE_RETAIL  6528
2421894  US          CTN00014      662
1812239  WHOLESALE   TYPE_WHOLESALE 159
1812238  RETAIL      BANLE          123
2308212  Selly       CTN00013       104
2281219  Ky Gui      KY_GUI          11
1812239  WHOLESALE   BANBUON          2
1812240  VIP         VIP               1
```

Collapsed by group id: `1812238`=6651, `1812239`=161, `2421894`=662, `2308212`=104, `2281219`=11, `1812240`=1. **Same 6 group ids as the phase doc** — no new group appeared, no STOP condition. Counts drifted slightly from the plan's original snapshot (natural customer growth since 2026-07-06), group set identical.

## Migration content — `crm/migrations/0040_seed_sapo_tag_mapping.up.sql` / `.down.sql`

1. **4 new `crm_tag` rows**, continuing the existing `tag-00000000-000N` sequence from migration 0003 (next free ids 6-9, no collision — verified via grep across all migrations):
   - `tag-00000000-0006` "KH Sỉ" / `demographic`
   - `tag-00000000-0007` "KH US giao hộ" / `demographic`
   - `tag-00000000-0008` "Selly" / `source`
   - `tag-00000000-0009` "Ký Gửi" / `demographic`
   - (none use `vip_tier`/`risk` — per phase doc's defense-in-depth rationale vs plan 260706-1738)

2. **6 `crm_ext_tag` rows** (`source_system='sapo_v2'`, `ext_key`=group id as TEXT, deterministic `ext_tag_id='exttag-sapo_v2-<group_id>'`) — one per verified group including RETAIL.

3. **5 `crm_ext_tag_map` rows** (`direction='inbound'`, `is_active=1`, deterministic `map_id='extmap-sapo_v2-<group_id>'`):
   - `1812239` WHOLESALE → `tag-00000000-0006` KH Sỉ
   - `2421894` US → `tag-00000000-0007` KH US giao hộ
   - `2308212` Selly → `tag-00000000-0008` Selly
   - `2281219` Ký Gửi → `tag-00000000-0009` Ký Gửi
   - `1812240` VIP → `tag-00000000-0001` (pre-existing seed VIP tag, verified exists with `category='vip_tier'` via migration 0014 — confirmed live in DB, not just assumed)

### Decision: RETAIL gets NO `crm_ext_tag_map` row (deviation from a literal reading of "map is_active=0")

Phase doc's mapping table lists RETAIL's `crm_tag canonical` column as `—` (none) — there is no tag to map to; tagging the Sapo default group is explicitly called out as "zero-information." The phase doc also says "RETAIL có entry nhưng map is_active=0," which read literally implies an inactive map row should exist. Resolved this ambiguity as: create the `crm_ext_tag` entry (satisfies "every real group has an entry" + lets sync recognize the id, no `skipped-no-mapping` noise) but skip the `crm_ext_tag_map` row entirely rather than inventing a placeholder target tag — there is no crm_tag for RETAIL to reference, and fabricating one would contradict the "zero information" rationale. This is functionally identical to an inactive map row (either way `is_active=1` count = 5, either way sync applies no tag for RETAIL customers) and avoids a fake FK target. Reactivating RETAIL later is a follow-up `INSERT` (create tag + map), not a migration — consistent with "bật lại được bằng UPDATE, không cần migration" (no schema change needed either way).

## Apply

`docker compose restart crm` → logs: `[entrypoint] running migrations …` / `[entrypoint] migrations OK` (twice — container restarted once more during log tail, both clean).

## Verification (queried real `/data/crm.db` inside the `crm` container — `CRM_DATA_DIR=/data`, not `/app/var`)

- `SELECT count(*) FROM crm_ext_tag_map WHERE is_active=1` → **5** ✓ (matches Success Criteria exactly)
- `crm_ext_tag` → **6 rows**, one per verified group (1812238/1812239/2421894/2308212/2281219/1812240) ✓
- 4 new `crm_tag` rows present with correct `category` (`demographic`×3, `source`×1); `tag-00000000-0001` VIP unchanged (`vip_tier`, `#FFD700`) ✓
- Full map listing confirms correct ext_tag_id → crm_tag_id pairing for all 5 active rows.

## Tests

`docker compose exec crm python3 -m pytest crm/src/tests -q --ignore=crm/src/tests/test_approach_script_file_repository.py` blocked at collection by an unrelated import error, so ran full suite with only the broken collection module skipped:

```
docker compose exec crm python3 -m pytest crm/src/tests -q --ignore=crm/src/tests/test_approach_script_handler.py
```
→ **796 passed, 1 failed** (`test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit`) — both the collection error (`test_approach_script_handler.py`, missing `wire_approach_script_router` export) and the 1 failure are in the unrelated approach-script feature area (different plan, `260706-0837-approach-script-codex-autogen`), matching the "2 known pre-existing unrelated failures" flagged in the dispatch. **No new failures** — nothing tag/ACL-related regressed.

## Files created
- `crm/migrations/0040_seed_sapo_tag_mapping.up.sql`
- `crm/migrations/0040_seed_sapo_tag_mapping.down.sql`

Not committed (left for review per instructions).

Status: DONE
Summary: Migration 0040 seeds crm_ext_tag (6 groups) + crm_ext_tag_map (5 active) + 4 new crm_tag rows per phase doc; re-verify confirmed same 6 groups (counts drifted, no new group); applied + live-verified in /data/crm.db; test suite shows 796 passed, only the 2 pre-existing unrelated approach-script failures remain.
Concerns/Blockers: RETAIL intentionally has no crm_ext_tag_map row (see Decision section) rather than a literal inactive placeholder row — functionally equivalent, flagging in case the plan author wants the literal inactive-row form instead.

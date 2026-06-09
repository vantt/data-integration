---
title: "Phase 4 — Rename v2 src/stg files to _v2 suffix"
description: "Rename all v2 src_sapo_*/stg_sapo_* dbt models to _v2 suffix so v3 files add cleanly alongside. std_* stays unversioned. Internal-only; marts/serving/Metabase/detailView untouched."
status: complete
priority: P2
effort: 3h
---

# Phase 4 — Rename v2 src/stg files to `_v2` suffix

Final structural prep before v3. Marks every v2 ingestion/staging model file with a `_v2` suffix so v3 can add `*_v3` siblings without ambiguity. `std_*` is the source-agnostic union contract — **never** gets a version suffix.

## Context links
- Analysis: `plans/reports/arch-260603-1730-sapo-v2-v3-migration-gate.md`
- Naming rules: `docs/architecture/naming-conventions.md` §7
- Verification toolkit: `plans/260603-1730-sapo-std-gate-and-naming/verification-protocol.md`
- Depends on: **Phase 0** (std layer complete). Recommended last (after P3) so column-rename phases use stable file paths.

---

## DECISION D1 — RESOLVED (middle-ground)

**Status: RESOLVED = middle-ground.**

Scope of this phase:
1. `git mv` every `src_sapo_*.sql` / `stg_sapo_*.sql` → `*_v2.sql` (22 files).
2. Update all `ref('src_sapo_<e>')` / `ref('stg_sapo_<e>')` → `ref('src_sapo_<e>_v2')` / `ref('stg_sapo_<e>_v2')` across ~27 referencing dbt files.
3. In `transformation/models/sources.yml`: rename the **dbt source alias** `- name: sapo_raw` → `- name: sapo_v2_raw`, while keeping `external_location` pointed at the physical `.../sapo_raw/{name}/...` folder unchanged. Update the ~10 `source('sapo_raw', …)` refs in `src_sapo_*_v2` models → `source('sapo_v2_raw', …)`.
4. Update 2 maintenance/test scripts.
5. Drop orphaned old physical tables after full rebuild.

**NOT in scope (Option B — deferred):**
- Renaming the dlt pipeline files
- Renaming the physical `sapo_raw/` folder on disk
- Changing `dataset_name` in any dlt config
- Touching dlt state (`sapo_raw/_dlt_pipeline_state`)

The physical raw folder stays at `.../sapo_raw/`. The dbt source alias is `sapo_v2_raw` pointing at that same folder. A fresh ingestion run still appends to `sapo_raw/` — verified in Step 4.6.

---

## Overview
- **Priority:** P2
- **Risk level:** Low–Medium. Pure internal rename — no published column changes. BUT renaming incremental `src_sapo_*` models forces a full rebuild + orphans old physical tables.
- **Lock strategy:** Strategy A (pause schedules) for all `dbt build` steps. Parse, parquet reads, and `git mv` are lock-free.
- **Blast radius:** INTERNAL only. Metabase / detailView / serving / `.known_tables.json` are untouched (they consume marts/std only).
- **Dagster:** uses `@dbt_assets` over `fqn:*` — no hardcoded src/stg asset names. Renames picked up automatically after Dagster container reload. Asset materialization history resets for renamed keys (benign).

---

## Files to rename (22 total)

### src models (10)
| Old name | New name |
|----------|----------|
| `src_sapo_accounts.sql` | `src_sapo_accounts_v2.sql` |
| `src_sapo_customer_groups.sql` | `src_sapo_customer_groups_v2.sql` |
| `src_sapo_customers.sql` | `src_sapo_customers_v2.sql` |
| `src_sapo_fulfillments.sql` | `src_sapo_fulfillments_v2.sql` |
| `src_sapo_order_returns.sql` | `src_sapo_order_returns_v2.sql` |
| `src_sapo_orders.sql` | `src_sapo_orders_v2.sql` |
| `src_sapo_price_lists.sql` | `src_sapo_price_lists_v2.sql` |
| `src_sapo_products.sql` | `src_sapo_products_v2.sql` |
| `src_sapo_purchase_orders.sql` | `src_sapo_purchase_orders_v2.sql` |
| `src_sapo_stock_adjustments.sql` | `src_sapo_stock_adjustments_v2.sql` |

### stg models (12)
| Old name | New name |
|----------|----------|
| `stg_sapo_accounts.sql` | `stg_sapo_accounts_v2.sql` |
| `stg_sapo_customers.sql` | `stg_sapo_customers_v2.sql` |
| `stg_sapo_fulfillments.sql` | `stg_sapo_fulfillments_v2.sql` |
| `stg_sapo_order_discount_items.sql` | `stg_sapo_order_discount_items_v2.sql` |
| `stg_sapo_order_items.sql` | `stg_sapo_order_items_v2.sql` |
| `stg_sapo_order_returns.sql` | `stg_sapo_order_returns_v2.sql` |
| `stg_sapo_orders.sql` | `stg_sapo_orders_v2.sql` |
| `stg_sapo_payments.sql` | `stg_sapo_payments_v2.sql` |
| `stg_sapo_products.sql` | `stg_sapo_products_v2.sql` |
| `stg_sapo_variant_prices.sql` | `stg_sapo_variant_prices_v2.sql` |
| `stg_sapo_variants.sql` | `stg_sapo_variants_v2.sql` |
| `stg_sapo_inventories.sql` | `stg_sapo_inventories_v2.sql` |

---

## PRE-STEP: Capture parquet baseline

Run T3 checksum (verification-protocol.md §T3) for all marts that depend on src/stg models (directly or transitively):
`fact_orders, fact_sales, fact_order_economics, fact_order_returns, fact_order_costs, dim_products, dim_customers, dim_price_lists, fact_variant_prices_snapshot, mart_inventory_health`

Save to `snapshots/pre_p4.txt`. Lock-free.

Also record the physical raw folder state — mtime and file count (D1 verification baseline):
```bash
# Run in PowerShell on host
Get-ChildItem "app_data\data_lake\sapo_raw" -Recurse -File | Measure-Object -Property LastWriteTime -Maximum | Select-Object Count, Maximum
# Or list the _dlt_pipeline_state mtime:
Get-Item "app_data\data_lake\sapo_raw\_dlt_pipeline_state" | Select-Object LastWriteTime
```
Save output to `snapshots/pre_p4_raw_mtime.txt`.

---

## STEP 4.1 — `git mv` all 22 src/stg files

**Lock-free — pure filesystem operation.**

```bash
cd transformation/models/staging

# src models
git mv src_sapo_accounts.sql src_sapo_accounts_v2.sql
git mv src_sapo_customer_groups.sql src_sapo_customer_groups_v2.sql
git mv src_sapo_customers.sql src_sapo_customers_v2.sql
git mv src_sapo_fulfillments.sql src_sapo_fulfillments_v2.sql
git mv src_sapo_order_returns.sql src_sapo_order_returns_v2.sql
git mv src_sapo_orders.sql src_sapo_orders_v2.sql
git mv src_sapo_price_lists.sql src_sapo_price_lists_v2.sql
git mv src_sapo_products.sql src_sapo_products_v2.sql
git mv src_sapo_purchase_orders.sql src_sapo_purchase_orders_v2.sql
git mv src_sapo_stock_adjustments.sql src_sapo_stock_adjustments_v2.sql

# stg models
git mv stg_sapo_accounts.sql stg_sapo_accounts_v2.sql
git mv stg_sapo_customers.sql stg_sapo_customers_v2.sql
git mv stg_sapo_fulfillments.sql stg_sapo_fulfillments_v2.sql
git mv stg_sapo_order_discount_items.sql stg_sapo_order_discount_items_v2.sql
git mv stg_sapo_order_items.sql stg_sapo_order_items_v2.sql
git mv stg_sapo_order_returns.sql stg_sapo_order_returns_v2.sql
git mv stg_sapo_orders.sql stg_sapo_orders_v2.sql
git mv stg_sapo_payments.sql stg_sapo_payments_v2.sql
git mv stg_sapo_products.sql stg_sapo_products_v2.sql
git mv stg_sapo_variant_prices.sql stg_sapo_variant_prices_v2.sql
git mv stg_sapo_variants.sql stg_sapo_variants_v2.sql
git mv stg_sapo_inventories.sql stg_sapo_inventories_v2.sql
```

**Checkpoint (parse only — ref() strings not yet updated so parse WILL fail; this is expected):**
```bash
git status | grep "renamed:"
# Must show all 22 renames. Count: 22
git status | grep "renamed:" | wc -l
```

**PASS:** `git status` shows exactly 22 renames; no unexpected deletions.
**ROLLBACK:** `git checkout HEAD -- transformation/models/staging/` (reverts all renames).
**COMMIT:** `git commit -m "refactor(staging): git mv src_sapo_* + stg_sapo_* → _v2 suffix (22 files)"`

---

## STEP 4.2 — Update `sources.yml` source alias (D1 middle-ground)

**Change — `transformation/models/sources.yml` (or wherever the sapo_raw source is declared):**

Locate the source block:
```bash
grep -n "sapo_raw\|sapo_v2_raw" transformation/models/sources.yml
```

Rename the alias only:
```yaml
# Before:
sources:
  - name: sapo_raw
    ...

# After:
sources:
  - name: sapo_v2_raw
    # external_location entries remain UNCHANGED — still point to sapo_raw/{table}/ on disk
    ...
```

**Do NOT change any `external_location` value.** The physical folder path stays `sapo_raw/`.

**Update `source()` refs in the 10 `src_sapo_*_v2.sql` files** (these are the files just renamed in Step 4.1):
```bash
# Find all source('sapo_raw', ...) in the renamed src files
grep -rn "source('sapo_raw'" transformation/models/staging/src_sapo_*_v2.sql
# Replace all → source('sapo_v2_raw', ...)
# PowerShell:
Get-ChildItem transformation\models\staging\src_sapo_*_v2.sql | ForEach-Object { (Get-Content $_.FullName) -replace "source\('sapo_raw'", "source('sapo_v2_raw'" | Set-Content $_.FullName }
```

**Checkpoint (parse — should now resolve source alias):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# Still expect ref() errors (Step 4.3 not done yet) but source() errors should be gone
```

**PASS:** parse output shows no `source 'sapo_raw' not found` errors; may still show `ref()` errors — acceptable at this step.
**ROLLBACK:** `git checkout -- transformation/models/sources.yml transformation/models/staging/src_sapo_*_v2.sql`
**COMMIT:** `git commit -m "refactor(sources): rename sapo_raw alias→sapo_v2_raw; keep external_location unchanged (D1 middle-ground)"`

---

## STEP 4.3 — Bulk-update all `ref()` strings across ~27 referencing files

**Find every file referencing old src/stg names:**
```bash
grep -rl "ref('src_sapo_\|ref('stg_sapo_" transformation/models/ --include="*.sql" | grep -v "_v2\."
# This lists files still using old ref() names (excluding the renamed files themselves which are fine)
```

**Apply bulk replace (PowerShell):**
```powershell
# In transformation/models/ — update ref() strings to add _v2 suffix
# Pattern: ref('src_sapo_<entity>') → ref('src_sapo_<entity>_v2')
#          ref('stg_sapo_<entity>') → ref('stg_sapo_<entity>_v2')
Get-ChildItem -Recurse transformation\models\ -Filter "*.sql" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    # Only update refs that don't already have _v2 suffix
    $new = $content -replace "ref\('(src_sapo_[a-z_]+?)'\)", "ref('`$1_v2')" `
                    -replace "ref\('(stg_sapo_[a-z_]+?)'\)", "ref('`$1_v2')"
    if ($new -ne $content) {
        Set-Content $_.FullName $new
        Write-Host "Updated: $($_.FullName)"
    }
}
```

**Post-replace verification:**
```bash
# Must return zero non-_v2 src/stg refs remaining
grep -r "ref('src_sapo_[a-z_]*')" transformation/models/ --include="*.sql" | grep -v "_v2'"
grep -r "ref('stg_sapo_[a-z_]*')" transformation/models/ --include="*.sql" | grep -v "_v2'"
# Both must return 0 lines
```

**Checkpoint (parse must now be fully clean):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
```

**PASS:** parse exits 0 with zero errors. This is the structural gate — do not proceed to build until parse is clean.
**ROLLBACK:** `git checkout -- transformation/models/` (reverts all ref() changes); re-parse confirms old names work.
**COMMIT:** `git commit -m "refactor(refs): update all ref(src_sapo_*) + ref(stg_sapo_*) → _v2 across ~27 files"`

---

## STEP 4.4 — Update `schema.yml` + 2 maintenance scripts

**`transformation/models/staging/schema.yml`:**
```bash
grep -n "name: src_sapo_\|name: stg_sapo_" transformation/models/staging/schema.yml
```
Update each `name:` entry: `src_sapo_orders` → `src_sapo_orders_v2` etc. (all 22 entries).

**`scripts/testing/verify_hops_readonly.py`:**
```bash
grep -n "src_sapo_\|stg_sapo_" scripts/testing/verify_hops_readonly.py
```
Update hardcoded model names: `src_sapo_orders` → `src_sapo_orders_v2`; `stg_sapo_orders` → `stg_sapo_orders_v2`; `stg_sapo_customers` → `stg_sapo_customers_v2`.

**`scripts/maintenance/cleanup_and_verify.py`:**
```bash
grep -n "src_sapo_\|stg_sapo_\|startswith" scripts/maintenance/cleanup_and_verify.py
```
- Update any hardcoded `stg_sapo_orders` row-count check → `stg_sapo_orders_v2`.
- Review `startswith('stg_sapo_'/'src_sapo_')` logic: these prefixes still match `*_v2` names (OK — current tables keep the same prefix). However, orphaned old tables (pre-rename names) also match this prefix → they will NOT be auto-cleaned. Document this: Step 4.7 manually drops orphans.

**Checkpoint (parse):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
```

**PASS:** parse exits 0.
**ROLLBACK:** `git checkout -- transformation/models/staging/schema.yml scripts/testing/verify_hops_readonly.py scripts/maintenance/cleanup_and_verify.py`
**COMMIT:** `git commit -m "refactor(staging): update schema.yml names + verify_hops + cleanup scripts to _v2"`

---

## STEP 4.5 — Full-refresh rebuild of renamed incrementals

Renaming an incremental model changes its `{{ this }}` table reference. dbt will build a NEW empty `*_v2` table from scratch on first run. This step forces that rebuild.

**Strategy A (extended pause — this takes longer than a normal build):**
```bash
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"

# Full-refresh src models first (they are the base incrementals)
docker exec data_platform sh -c "cd /app && dbt build --select src_sapo_accounts_v2 src_sapo_customers_v2 src_sapo_fulfillments_v2 src_sapo_order_returns_v2 src_sapo_orders_v2 src_sapo_price_lists_v2 src_sapo_products_v2 src_sapo_purchase_orders_v2 src_sapo_stock_adjustments_v2 src_sapo_customer_groups_v2 --full-refresh --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -20"

# Then build all stg + std + downstream in one pass (stg are views; std are views; marts rebuild)
docker exec data_platform sh -c "cd /app && dbt build --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -20"

docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**Checkpoint (T3 parquet checksums + T4 Dagster run):**
```bash
# T3 — compare all 10 affected marts to pre_p4.txt baseline
python -c "
import duckdb, glob, os
MARTS = ['fact_orders','fact_sales','fact_order_economics','fact_order_returns',
         'fact_order_costs','dim_products','dim_customers','dim_price_lists',
         'fact_variant_prices_snapshot','mart_inventory_health']
BASE = r'app_data\data_lake\export\marts\rolling'
con = duckdb.connect()
for m in MARTS:
    f = sorted(glob.glob(os.path.join(BASE, m, '*.parquet')))[-1]
    print(m, con.execute(f'SELECT COUNT(*), SUM(hash(1)) FROM read_parquet(\"{f}\")').fetchone())
"
# T4 — next realtime run after resume
docker logs data_platform --since 5m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**PASS:** all 10 mart row counts match `pre_p4.txt`; at least one `ingest_sapo_realtime_job` RUN_SUCCESS after schedule resume.
**ROLLBACK:** `git revert` Steps 4.1–4.4 in reverse; re-parse; Strategy A full-refresh rebuild of old model names (old tables still exist until Step 4.7).

---

## STEP 4.6 — D1 verification: raw folder untouched + ingestion still appends

**Verify `sapo_raw/` is physically untouched (D1 middle-ground check):**
```powershell
# Compare mtime of _dlt_pipeline_state to pre_p4_raw_mtime.txt baseline
Get-Item "app_data\data_lake\sapo_raw\_dlt_pipeline_state" | Select-Object LastWriteTime
# Must match baseline (no dlt state touched)

# Verify external_location in sources.yml still points to sapo_raw/
grep "external_location" transformation/models/sources.yml | grep "sapo_raw"
# Must return entries with sapo_raw/ in the path (NOT sapo_v2_raw/)
```

**Verify a fresh ingestion still appends to `sapo_raw/` (trigger one realtime run and check):**
```bash
# Check that after a realtime run, new files appear in sapo_raw/ not sapo_v2_raw/
docker logs data_platform --since 3m 2>&1 | grep -i "sapo_raw\|sapo_v2_raw\|appended\|loaded"
# Should show sapo_raw/ writes (the dlt pipeline is unchanged)
```

**PASS:** `_dlt_pipeline_state` mtime unchanged from baseline; `external_location` values contain `sapo_raw/`; realtime run logs show `sapo_raw/` writes.
**If FAIL:** Stop immediately. The sources.yml external_location may have been accidentally edited. `git diff transformation/models/sources.yml` to inspect; revert if needed.
**COMMIT (no code change — verification only):** Document result in a comment in this phase file or in `snapshots/post_p4_d1_verification.txt`.

---

## STEP 4.7 — Drop orphaned old physical tables

The pre-rename `src_sapo_*` / `stg_sapo_*` tables (without `_v2`) are now orphaned in the DuckDB warehouse. The `startswith` prefix logic in `cleanup_and_verify.py` will NOT auto-remove them (they still match the prefix). Drop manually:

```python
import duckdb

# Connect to the warehouse DuckDB (adjust path if different)
# NOTE: warehouse is single-writer — schedules MUST be paused (no in-flight run) or this connect fails on lock.
con = duckdb.connect(r"app_data\data_lake\sapo_warehouse.duckdb")

OLD_TABLES = [
    # src models (10)
    "main_staging.src_sapo_accounts",
    "main_staging.src_sapo_customer_groups",
    "main_staging.src_sapo_customers",
    "main_staging.src_sapo_fulfillments",
    "main_staging.src_sapo_order_returns",
    "main_staging.src_sapo_orders",
    "main_staging.src_sapo_price_lists",
    "main_staging.src_sapo_products",
    "main_staging.src_sapo_purchase_orders",
    "main_staging.src_sapo_stock_adjustments",
    # stg models (12) — views, but drop to be clean
    "main_staging.stg_sapo_accounts",
    "main_staging.stg_sapo_customers",
    "main_staging.stg_sapo_fulfillments",
    "main_staging.stg_sapo_order_discount_items",
    "main_staging.stg_sapo_order_items",
    "main_staging.stg_sapo_order_returns",
    "main_staging.stg_sapo_orders",
    "main_staging.stg_sapo_payments",
    "main_staging.stg_sapo_products",
    "main_staging.stg_sapo_variant_prices",
    "main_staging.stg_sapo_variants",
    "main_staging.stg_sapo_inventories",
]

for t in OLD_TABLES:
    try:
        con.execute(f"DROP TABLE IF EXISTS {t}")
        con.execute(f"DROP VIEW IF EXISTS {t}")
        print(f"Dropped: {t}")
    except Exception as e:
        print(f"Skip {t}: {e}")

con.close()
```

**Checkpoint:**
```bash
# Verify no orphaned old tables remain
docker exec data_platform sh -c "duckdb /app/var/warehouse.duckdb -c \"SELECT table_name FROM information_schema.tables WHERE table_schema='main_staging' AND table_name LIKE 'src_sapo_%' AND table_name NOT LIKE '%_v2%'\" 2>&1"
docker exec data_platform sh -c "duckdb /app/var/warehouse.duckdb -c \"SELECT table_name FROM information_schema.tables WHERE table_schema='main_staging' AND table_name LIKE 'stg_sapo_%' AND table_name NOT LIKE '%_v2%'\" 2>&1"
# Both must return 0 rows
```

**PASS:** both queries return 0 rows.
**ROLLBACK:** Not applicable — orphan tables are safe to leave if this step fails (they are inert; just consume disk space). Do not recreate them.
**COMMIT:** `git commit -m "refactor(warehouse): drop orphaned pre-rename src_sapo_* + stg_sapo_* tables"`

---

## STEP 4.8 — Dagster container reload + final run confirmation

Restart the Dagster container so the asset graph reloads with new model names. The old asset keys (without `_v2`) will no longer appear in the graph; new `_v2` keys will register.

```bash
docker compose restart data_platform
# Wait ~30s for container to be healthy
docker logs data_platform --since 60s 2>&1 | grep -iE "started|ERROR|ready"
```

**Wait for one full realtime cycle (≤3 min) then check:**
```bash
docker exec data_platform sh -c "dagster run list --limit 3"
docker logs data_platform --since 5m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**Checkpoint (T3 final):**
Run T3 one more time. Save to `snapshots/post_p4.txt`. Compare to `pre_p4.txt`:
- All 10 mart row counts: identical
- All 10 mart checksums: identical (no column changes — this is a pure internal rename)

**PASS (all required):**
- Dagster container healthy after restart
- `ingest_sapo_realtime_job` RUN_SUCCESS
- All 10 parquet checksums match `pre_p4.txt`
- Zero orphaned old tables in warehouse
- `sapo_raw/_dlt_pipeline_state` mtime unchanged from `pre_p4_raw_mtime.txt`

---

## File ownership

| Action | Files |
|--------|-------|
| `git mv` (22 files) | `transformation/models/staging/src_sapo_*.sql` → `*_v2.sql`; `transformation/models/staging/stg_sapo_*.sql` → `*_v2.sql` |
| Modify (source alias) | `transformation/models/sources.yml` |
| Modify (ref updates, ~27 files) | All `transformation/models/**/*.sql` containing `ref('src_sapo_*')` or `ref('stg_sapo_*')` |
| Modify (schema) | `transformation/models/staging/schema.yml` |
| Modify (scripts) | `scripts/testing/verify_hops_readonly.py`, `scripts/maintenance/cleanup_and_verify.py` |
| Do NOT touch | `transformation/models/staging/standard/std_*.sql` (file names), Metabase blueprints, detailView, serving scripts, `.known_tables.json` |

---

## Success criteria

- All 22 src/stg models named `*_v2`; `std_*` unversioned; `dbt parse` exits 0; `dbt build` + tests clean
- Source alias `sapo_v2_raw` resolves to same physical `sapo_raw/` folder; `external_location` values unchanged
- `sapo_raw/_dlt_pipeline_state` mtime unchanged (dlt not touched)
- A fresh realtime ingestion run still appends to `sapo_raw/` (not a new path)
- All 10 affected mart parquets byte-identical to `pre_p4.txt` baseline
- Zero orphaned `src_sapo_*` / `stg_sapo_*` (non-`_v2`) tables in warehouse
- Metabase / detailView load unchanged (no redeploy needed — confirmed by T7 smoke test)

---

## Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Incremental full-refresh = heavy raw reprocessing → long build time | High | Low | Run during low-traffic window; output validated identical by T3 |
| Orphan tables linger (prefix logic won't auto-clean) | High | Low | Explicit DROP in Step 4.7 with verification query |
| Accidental std model rename breaks v3 gate | Low | High | Step 4.1 `git mv` list excludes `standard/` directory; verify with `git status` |
| Missed `ref()` after bulk replace → `dbt parse` fails | Medium | Low | Parse gate in Step 4.3 catches all misses before any build |
| `sources.yml` `external_location` accidentally changed → ingestion breaks | Low | High | D1 verification in Step 4.6 checks both mtime and path; revert immediately if fails |
| DuckDB write-lock during full-refresh (Step 4.5) conflicts with realtime job | Medium | Medium | Strategy A: schedules paused before full-refresh; resumed after |

---

## Rollback plan

Each step is a separate commit — revert in reverse order:
1. Step 4.7: orphan tables — skip rollback (inert; no functional impact)
2. Step 4.5 build: `git revert` Steps 4.2–4.4; strategy A full-refresh old model names (old tables still exist)
3. Step 4.3 ref updates: `git revert` Step 4.3 commit; re-parse
4. Step 4.2 sources.yml: `git revert` Step 4.2 commit; re-parse
5. Step 4.1 `git mv`: `git revert` Step 4.1 commit; re-parse

Full rollback estimated: ~60 min (full-refresh required to rebuild old incremental tables from raw).

---

## Next steps

After Phase 4, the project is structurally complete for v3:
- v2 src/stg layer: `src_sapo_*_v2` / `stg_sapo_*_v2` (frozen when v3 arrives)
- v3 layer (future): add `src_sapo_*_v3` / `stg_sapo_*_v3` reading a NEW `sapo_v3_raw` source
- UNION in each `std_*` (gated by business answers Q1–Q5)
- dlt pipeline rename to `sapo_v2_raw` physical folder is a separate optional sub-phase (Option B) requiring explicit approval

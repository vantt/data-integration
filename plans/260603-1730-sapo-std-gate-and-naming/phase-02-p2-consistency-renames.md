---
title: "Phase 2 — P2 consistency renames"
description: "Standardize _timestamp→_at timestamps, total_orders_count→order_count, fact_sales.revenue→net_revenue, last_modified→last_modified_at."
status: pending
priority: P2
effort: 4h
---

# Phase 2 — P2 consistency renames

## Context links
- Naming rules: `docs/architecture/naming-conventions.md` §§3,4,5
- Verification toolkit: `plans/260603-1730-sapo-std-gate-and-naming/verification-protocol.md`
- Blocked by: Phase 1 complete

---

## Overview
- **Priority:** P2 — convention drift; not semantically wrong, but inconsistent
- **Status:** pending — blocked by Phase 1
- **Lock strategy:** Strategy A for all `dbt build` steps. Parse is lock-free.
- **Largest blast radius:** R7 `order_timestamp → ordered_at` — 24 Metabase blueprint files + 3 dbt models.
- **Structure:** std-layer step first (R10 only, cheap), then single coordinated mart cascade, then serving rebuild, then detailView, then blueprints. All mart steps in one window — one serving rebuild cycle.

---

## Rename table

| # | Current | New | Scope | Rule |
|---|---------|-----|-------|------|
| R7 | `order_timestamp` | `ordered_at` | `fact_orders` → `int_customer_metrics`, `int_us_shipment_line_prices`, 24 blueprints, detailView (alias-preserving) | §3 `_at` for event timestamps |
| R8 | `return_timestamp` | `returned_at` | `fact_order_returns` only | §3 |
| R9 | `last_modified` | `last_modified_at` | `dim_customers` (alias + incremental WHERE) + consumers | §3 |
| R10 | `total_orders_count` | `order_count` | `std_customers` → `dim_customers`, `mart_customer_action_queue`, `mart_customer_status_snapshot_monthly`, detailView, blueprints | §5 counts → `_count` |
| R11 | `fact_sales.revenue` | `net_revenue` | `fact_sales` → `mart_sku_economics_monthly`, `int_customer_metrics` (if referenced), detailView, blueprints | §4 revenue = domain noun |

**R7 detailView note:** `order_header.sql` aliases `fo.order_timestamp AS created_at` — change ONLY the source column name to `fo.ordered_at AS created_at`. Keep the `AS created_at` alias to avoid touching `order_mappers.py` and `OrderHeader.created_at`. This is an alias-preserving rename.

---

## PRE-STEP: Capture parquet baseline

Run T3 checksum (verification-protocol.md §T3) for all marts affected by any rename in this phase:
`fact_orders, fact_order_returns, fact_sales, dim_customers, dim_customers_base, mart_customer_action_queue, mart_customer_status_snapshot_monthly, mart_sku_economics_monthly, int_customer_metrics`

Save to `snapshots/pre_p2.txt`. Lock-free — run anytime.

---

## STEP 2.1 — `std_customers`: `total_orders_count → order_count` (R10 at std)

**Change:**
- `transformation/models/staging/standard/std_customers.sql`: `coalesce(orders_count, 0) as total_orders_count,` → `coalesce(orders_count, 0) as order_count,`
- `transformation/models/staging/standard/schema.yml`: `std_customers` column entry `total_orders_count` → `order_count`

**Checkpoint (parse + Strategy A build):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_customers --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0. Downstream consumers (`dim_customers_base`, `dim_customers`) will break on build (expected; fixed in Step 2.4). Parse passes because DuckDB resolves view columns at query time.
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/std_customers.sql transformation/models/staging/standard/schema.yml`
**COMMIT:** `git commit -m "feat(std): rename total_orders_count→order_count in std_customers (R10 std layer)"`

---

## STEP 2.2 — `fact_orders`: `order_timestamp → ordered_at` (R7)

**Change — `transformation/models/marts/sales/fact_orders.sql`:**
- The line `created_at as order_timestamp,` → `created_at as ordered_at,`

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_orders --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 — fact_orders row count must match pre_p2.txt; SUM(gross_revenue) unchanged
python -c "import duckdb,glob,os; f=sorted(glob.glob(r'app_data\data_lake\export\marts\rolling\fact_orders\*.parquet'))[-1]; print(duckdb.query(f'SELECT COUNT(*), SUM(gross_revenue), MIN(ordered_at), MAX(ordered_at) FROM read_parquet(\"{f}\")').df())"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; row count matches; `ordered_at` column present with same date range as former `order_timestamp`; `SUM(gross_revenue)` unchanged.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/fact_orders.sql`; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(fact_orders): R7 order_timestamp→ordered_at"`

---

## STEP 2.3 — `fact_order_returns`: `return_timestamp → returned_at` (R8)

**Change — `transformation/models/marts/sales/fact_order_returns.sql`:**
- `COALESCE(r.issued_at, r.created_at) AS return_timestamp,` → `COALESCE(r.issued_at, r.created_at) AS returned_at,`

**Pre-edit verify:** `return_date` (DATE column) stays unchanged — only the TIMESTAMPTZ alias changes.

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_order_returns --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 — fact_order_returns row count + SUM(refund_amount) must match pre_p2.txt
python -c "import duckdb,glob,os; f=sorted(glob.glob(r'app_data\data_lake\export\marts\rolling\fact_order_returns\*.parquet'))[-1]; print(duckdb.query(f'SELECT COUNT(*), SUM(refund_amount) FROM read_parquet(\"{f}\")').df())"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; row count + `SUM(refund_amount)` match baseline; `returned_at` column present.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/fact_order_returns.sql`; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(fact_order_returns): R8 return_timestamp→returned_at"`

---

## STEP 2.4 — `fact_sales`: `revenue → net_revenue` (R11)

**Change — `transformation/models/marts/sales/fact_sales.sql`:**
- The CASE expression ending `as revenue,` → `as net_revenue,`

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_sales --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 — fact_sales: row count must match; SUM(net_revenue) must equal pre-rename SUM(revenue)
python -c "import duckdb,glob,os; f=sorted(glob.glob(r'app_data\data_lake\export\marts\rolling\fact_sales\*.parquet'))[-1]; print(duckdb.query(f'SELECT COUNT(*), SUM(net_revenue) FROM read_parquet(\"{f}\")').df())"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; row count matches; `SUM(net_revenue)` equals pre-rename `SUM(revenue)` from baseline.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/fact_sales.sql`; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(fact_sales): R11 revenue→net_revenue"`

---

## STEP 2.5 — Downstream intermediates: `int_customer_metrics` (R7 + R11), `int_us_shipment_line_prices` (R7)

**Changes:**

`transformation/models/marts/core/intermediate/int_customer_metrics.sql`:
- R7: All `o.order_timestamp` → `o.ordered_at` (lines 46, 58, 59, 201–219 — scan all; typically 7+ occurrences including LAG, MIN, MAX, WHERE)
- R11: If `fs.revenue` is selected from `fact_sales` → `fs.net_revenue` (grep to confirm)

```bash
# Count occurrences before edit
grep -c "order_timestamp" transformation/models/marts/core/intermediate/int_customer_metrics.sql
grep -n "\.revenue\b" transformation/models/marts/core/intermediate/int_customer_metrics.sql
```

`transformation/models/intermediate/us_shipment/int_us_shipment_line_prices.sql`:
- R7: `o.order_timestamp` (line 22 in us_orders CTE) → `o.ordered_at`
- R7: `cast(uo.order_timestamp AS date)` (line 67) → `cast(uo.ordered_at AS date)`

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select int_customer_metrics int_us_shipment_line_prices --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# Verify no order_timestamp refs remain
grep -c "order_timestamp" transformation/models/marts/core/intermediate/int_customer_metrics.sql
grep -c "order_timestamp" transformation/models/intermediate/us_shipment/int_us_shipment_line_prices.sql
# Both must return 0
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; both grep counts = 0; T4 next realtime run succeeds.
**ROLLBACK:** `git checkout --` the two files; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(intermediates): R7 order_timestamp→ordered_at in int_customer_metrics + int_us_shipment_line_prices"`

---

## STEP 2.6 — `dim_customers`: R9 (`last_modified → last_modified_at`) + R10 (`total_orders_count → order_count`)

**Critical: R9 requires updating BOTH the alias definition AND the incremental WHERE clause. Missing either causes stale incremental builds.**

**Changes — `transformation/models/marts/core/dim_customers.sql`:**

R9:
- Alias: `GREATEST(...) as last_modified` → `GREATEST(...) as last_modified_at`
- Incremental WHERE: `WHERE last_modified >= (SELECT MAX(last_modified) FROM {{ this }})` → `WHERE last_modified_at >= (SELECT MAX(last_modified_at) FROM {{ this }})`

R10:
- `COALESCE(frequency, 0) as total_orders_count,` → `COALESCE(frequency, 0) as order_count,`

**Verify consumers of `dim_customers.last_modified`:**
```bash
grep -rn "last_modified\b" transformation/models/marts/customer/ transformation/models/marts/core/dim_customers_base.sql
```
Update any references found.

**Checkpoint (full-refresh required because dim_customers is incremental):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
# Full-refresh needed: incremental WHERE now references last_modified_at which doesn't exist in the old table
docker exec data_platform sh -c "cd /app && dbt build --select dim_customers --full-refresh --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# T3 — dim_customers row count must match pre_p2.txt
python -c "import duckdb,glob,os; f=sorted(glob.glob(r'app_data\data_lake\export\marts\rolling\dim_customers\*.parquet'))[-1]; print(duckdb.query(f'SELECT COUNT(*), MIN(last_modified_at), MAX(last_modified_at) FROM read_parquet(\"{f}\")').df())"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; row count matches baseline; `last_modified_at` and `order_count` columns present.
**ROLLBACK:** `git checkout -- transformation/models/marts/core/dim_customers.sql`; Strategy A full-refresh rebuild.
**COMMIT:** `git commit -m "feat(dim_customers): R9 last_modified→last_modified_at, R10 total_orders_count→order_count"`

---

## STEP 2.7 — Customer marts: `mart_customer_action_queue` + `mart_customer_status_snapshot_monthly` (R10)

**Changes:**

`mart_customer_action_queue.sql`: all `total_orders_count` → `order_count` (SELECT lines 24, 75; WHERE/CASE lines 37, 54, 56)
```bash
grep -c "total_orders_count" transformation/models/marts/customer/mart_customer_action_queue.sql
# Before: N>0; after edit: 0
```

`mart_customer_status_snapshot_monthly.sql`: all `total_orders_count` → `order_count` (lines 24, 38, 91, 94, 117)
```bash
grep -c "total_orders_count" transformation/models/marts/customer/mart_customer_status_snapshot_monthly.sql
# Before: N>0; after edit: 0
```

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select mart_customer_action_queue mart_customer_status_snapshot_monthly --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# T3 checksums — row counts match pre_p2.txt for both marts
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; both row counts match; grep count = 0 in both files.
**ROLLBACK:** `git checkout --` the two files; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(customer-marts): R10 total_orders_count→order_count in action_queue + status_snapshot"`

---

## STEP 2.8 — `mart_sku_economics_monthly`: R11 (`fs.revenue → fs.net_revenue`)

**Change — `transformation/models/marts/sales/mart_sku_economics_monthly.sql`:**
```bash
grep -n "fs\.revenue\|\.revenue\b" transformation/models/marts/sales/mart_sku_economics_monthly.sql
```
Update all `fs.revenue` → `fs.net_revenue`.

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select mart_sku_economics_monthly --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 — mart_sku_economics_monthly row count must match pre_p2.txt
python -c "import duckdb,glob,os; f=sorted(glob.glob(r'app_data\data_lake\export\marts\rolling\mart_sku_economics_monthly\*.parquet'))[-1]; print(duckdb.query(f'SELECT COUNT(*), SUM(net_revenue) FROM read_parquet(\"{f}\")').df())"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; row count matches; `SUM(net_revenue)` equals pre-rename `SUM(revenue)`.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/mart_sku_economics_monthly.sql`; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(mart_sku_economics_monthly): R11 revenue→net_revenue"`

---

## STEP 2.9 — Serving rebuild (T8)

```bash
docker compose stop metabase
python scripts/provisioning/bootstrap_serving_views.py
# Check output for errors — must be zero "binder" or "Error" lines
docker compose start metabase
```

**Spot-check olap.duckdb:**
```bash
docker exec data_platform sh -c "duckdb /app/var/olap.duckdb -c 'SELECT ordered_at, order_count FROM fact_orders fo JOIN dim_customers dc ON fo.customer_key=dc.customer_key LIMIT 1' 2>&1"
docker exec data_platform sh -c "duckdb /app/var/olap.duckdb -c 'SELECT returned_at FROM fact_order_returns LIMIT 1' 2>&1"
docker exec data_platform sh -c "duckdb /app/var/olap.duckdb -c 'SELECT last_modified_at FROM dim_customers LIMIT 1' 2>&1"
```

**PASS:** all three queries return a row without error.
**ROLLBACK:** revert all mart SQL edits (Steps 2.2–2.8); re-run `bootstrap_serving_views.py`; restart Metabase.

---

## STEP 2.10 — detailView code updates + image rebuild (T9)

**Changes:**

`queries/order_header.sql` (R7 alias-preserving):
- `fo.order_timestamp AS created_at,` → `fo.ordered_at AS created_at,`
- Do NOT change `AS created_at` — preserves `OrderHeader.created_at` in Python mapper.

`queries/order_line_items.sql` (R11):
- `fs.revenue` → `fs.net_revenue`

`queries/customer_profile.sql` (R9, R10 if referenced):
```bash
grep -n "last_modified\|total_orders_count" detailView/app/adapters/outbound/duckdb/queries/customer_profile.sql
```
Update any matches.

`queries/customer_value_metrics.sql` (R10):
```bash
grep -n "total_orders_count" detailView/app/adapters/outbound/duckdb/queries/customer_value_metrics.sql
```
Update any matches → `order_count`.

`order_mappers.py` (R11):
- `row.get("revenue")` → `row.get("net_revenue")` in `map_line_item()`

`domain/order.py` (R11):
- `LineItem.revenue` field → `net_revenue`

Templates (R11): `grep -rn "\.revenue\b" detailView/app/web/templates/` — update display labels referencing line-item revenue.

**Rebuild + smoke test (T9):**
```bash
docker compose up -d --build detail_view
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<valid_order_code>/tab/financial
```

**PASS:** HTTP 200; no 500 errors; `net_revenue` visible in line items section.
**ROLLBACK:** `git checkout -- detailView/`; `docker compose up -d --build detail_view`.
**COMMIT:** `git commit -m "feat(detailView): R7/R10/R11 — ordered_at alias-preserve, order_count, net_revenue"`

---

## STEP 2.11 — Blueprint bulk updates + redeploy

**Identify all affected blueprints:**
```bash
grep -rl "order_timestamp\|return_timestamp\|last_modified\b\|total_orders_count\|\.revenue\b" docs/analytics-handbook/blueprints/
```

**Bulk replace per rename (apply in this order to avoid partial-rename conflicts):**

R7 (largest blast radius — 24 files):
```bash
# Preview first
grep -r "order_timestamp" docs/analytics-handbook/blueprints/ | wc -l
# Then replace (use PowerShell or sed)
# PowerShell:
Get-ChildItem -Recurse docs\analytics-handbook\blueprints\*.md | ForEach-Object { (Get-Content $_.FullName) -replace 'order_timestamp', 'ordered_at' | Set-Content $_.FullName }
```

R8: `return_timestamp` → `returned_at` (in `finance_return_impact.md`, `order_detail.md`)

R9: `last_modified` → `last_modified_at` (word-boundary — avoid matching `last_modified_at` itself if already partially updated)
```bash
# Use exact string match, not contains:
Get-ChildItem -Recurse docs\analytics-handbook\blueprints\*.md | ForEach-Object { (Get-Content $_.FullName) -replace '\blast_modified\b', 'last_modified_at' | Set-Content $_.FullName }
```

R10: `total_orders_count` → `order_count`

R11: `\.revenue\b` in `fact_sales` context → `net_revenue` (check for false positives — `gross_revenue`, `net_revenue` already correct; only change standalone `.revenue`)

**Post-replace verification (must all return zero):**
```bash
grep -r "order_timestamp" docs/analytics-handbook/blueprints/
grep -r "return_timestamp" docs/analytics-handbook/blueprints/
grep -r "\blast_modified\b" docs/analytics-handbook/blueprints/
grep -r "total_orders_count" docs/analytics-handbook/blueprints/
```

**Redeploy affected blueprints:**
```bash
# For each blueprint in the grep output from the identify step:
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/<file>.md
```

**Checkpoint:** Open `order_listing` dashboard in Metabase — confirm `ordered_at` date filter works. Open customer dashboard — confirm `order_count` shows correct value.

**PASS:** all dashboards load; date filters on `ordered_at` functional; zero old-name grep hits.
**ROLLBACK:** `git checkout -- docs/analytics-handbook/blueprints/`; redeploy previous versions.
**COMMIT:** `git commit -m "feat(blueprints): R7–R11 bulk rename across 24+ blueprint files"`

---

## STEP 2.12 — Full post-deploy harness validation

**T3 — parquet checksums:**
Run T3 for all affected marts. Save to `snapshots/post_p2.txt`. Compare to `pre_p2.txt`:
- Row counts: identical for all marts
- Value checksums on key aggregate columns (revenue, refund_amount, order counts): identical despite column renames

**T4 — Dagster health:**
```bash
docker exec data_platform sh -c "dagster run list --limit 5"
docker logs data_platform --since 10m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**T5 — HOP counts:**
```bash
python scripts/testing/verify_hops_readonly.py
```

**PASS (all required):**
- All mart checksums match
- At least one Dagster realtime RUN_SUCCESS since changes applied
- HOP counts within expected bounds

**If `int_customer_metrics` incremental fails after R7:** run with `--full-refresh`:
```bash
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select int_customer_metrics --full-refresh --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

---

## Success criteria

- `dbt build` clean for all 10 modified models
- Harness: byte-identical row counts + key-column values for all affected marts
- Metabase: `ordered_at`-based date filters work in all 24 dashboards
- detailView: line-item `net_revenue` and customer `order_count` display correctly
- Post-deploy grep: zero remaining old column names in blueprints

---

## Rollback plan

1. Revert all SQL edits (git revert per step commit — each step is isolated)
2. Strategy A rebuild for affected DAG
3. Stop Metabase → `bootstrap_serving_views.py` → start Metabase
4. Rebuild detailView image
5. Redeploy previous blueprint versions

**R7 rollback is the most expensive** (24 blueprint files). Keep all blueprint changes in a single commit (Step 2.11) for clean revert. Estimated total rollback: ~45 min.

---

## Next steps
After P2: optionally Phase 3 (P3 minor cosmetic renames). Safe to skip indefinitely.

---
title: "Phase 1 — P1 wrong/ambiguous term renames"
description: "Fix semantically incorrect or ambiguous column names at std contract then cascade to published marts, serving, blueprints, detailView."
status: pending
priority: P1
effort: 5h
---

# Phase 1 — P1 term renames

## Context links
- Naming rules: `docs/architecture/naming-conventions.md`
- Verification toolkit: `plans/260603-1730-sapo-std-gate-and-naming/verification-protocol.md`
- Blocked by: Phase 0 complete

---

## Overview
- **Priority:** P1 — semantically wrong names must not bake into the v3 contract
- **Status:** pending — blocked by Phase 0
- **Lock strategy:** Strategy A (pause schedules) for all `dbt build` steps. Parse is lock-free.
- **Two-wave structure:** Wave A = std-internal renames only (cheap, independently shippable). Wave B = published-mart cascade (expensive, single coordinated deploy window). Can ship Wave A and stop.

---

## Rename table

| # | Current | New | Locations | Rule |
|---|---------|-----|-----------|------|
| R1 | `total_expense` | `total_spend` | `std_customers` | §4 spend by customer |
| R2 | `item_id` | `order_line_id` | `std_order_items`, `fact_sales`, `int_us_shipment_line_prices`, detailView | §2 line-item degenerate key |
| R3 | `is_active_status` | `is_active` | `dim_products` (3 locations) | §5 booleans = `is_/has_` |
| R4 | `discount_nature` / `primary_discount_nature` | `discount_type` / `primary_discount_type` | `fact_orders`, `fact_order_costs`, detailView | §6 `_type` not `_nature` |
| R5 | `tax_amount` / `total_tax_amount` | `vat_amount` | `std_orders`, `fact_orders`, `fact_order_economics`, `fact_sales` (ratio), blueprints, detailView | §4 VAT-specific naming |
| R6 | `sol_timestamp` | `ordered_at` | `fact_sales`, `mart_sku_economics_monthly` | §3 `_at` for timestamps |

**DO NOT rename `order_code → order_number`.** Alphanumeric; `_number` misleads. See naming-conventions.md §2.

**R5 SCOPE GUARD:** rename ONLY the Sapo embedded VAT column (`total_tax_amount` in `std_orders` / `tax_amount` in `fact_orders`). Do NOT touch: cost_type label strings `'tax_vat'`/`'tax_pit'` in `fact_order_costs`; Shopee columns `vat_tax`, `personal_income_tax`; any non-Sapo tax column.

---

## WAVE A — std contract renames (cheap, independently shippable)

### PRE-WAVE A: Capture parquet baseline

Run T3 checksum (see verification-protocol.md §T3) for:
`fact_orders, fact_order_costs, fact_order_economics, fact_sales, dim_products, dim_customers, mart_sku_economics_monthly`

Save to `snapshots/pre_p1.txt`. Lock-free.

---

### STEP 1.A1 — `std_customers`: `total_expense → total_spend` (R1)

**Change:**
- `transformation/models/staging/standard/std_customers.sql`: rename the output alias `coalesce(total_expense, 0) as total_expense` → `coalesce(total_expense, 0) as total_spend`
- `transformation/models/staging/standard/schema.yml`: update `std_customers` column entry `total_expense` → `total_spend`

**Checkpoint:**
```bash
# T1 — parse (lock-free)
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

# Strategy A — build std_customers only
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_customers --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"

# Verify dim_customers_base + dim_customers do NOT propagate total_expense (should be unaffected):
grep -n "total_expense\|total_spend" transformation/models/marts/core/dim_customers_base.sql
grep -n "total_expense\|total_spend" transformation/models/marts/core/dim_customers.sql
```

**PASS:** `dbt build` exits 0; grep shows `dim_customers` and `dim_customers_base` do not reference `total_expense` (R1 is std-only).
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/std_customers.sql transformation/models/staging/standard/schema.yml`; re-parse.
**COMMIT:** `git commit -m "feat(std): rename total_expense→total_spend in std_customers (R1)"`

---

### STEP 1.A2 — `std_order_items`: `item_id → order_line_id` (R2 at std)

**Change:**
- `transformation/models/staging/standard/std_order_items.sql`: `item_id,` → `item_id AS order_line_id,`
- `transformation/models/staging/standard/schema.yml`: update `std_order_items` column entry `item_id` → `order_line_id`

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Strategy A
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_order_items --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0. `fact_sales` and `int_us_shipment_line_prices` will break when built (they still reference `item_id`) — this is expected and will be fixed in Wave B Step 1.B2. Parse still passes because `fact_sales` reads `std_order_items` via `ref()` and DuckDB resolves at query time, not parse time.
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/std_order_items.sql transformation/models/staging/standard/schema.yml`
**COMMIT:** `git commit -m "feat(std): rename item_id→order_line_id in std_order_items (R2 std layer)"`

---

### STEP 1.A3 — `std_orders`: `total_tax_amount → vat_amount` (R5 at std)

**Change:**
- `transformation/models/staging/standard/std_orders.sql`: the line `tax_amount as total_tax_amount,` → `tax_amount as vat_amount,`
- **Scope guard verification (before editing):**
  ```bash
  grep -n "tax_amount\|vat_amount" transformation/models/staging/standard/std_orders.sql
  ```
  Only touch the `total_tax_amount` output alias. Leave all other `tax_amount` occurrences (if any) as-is.

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Strategy A
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_orders --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0. `fact_orders` and `fact_sales` will break on build (expected; fixed in Wave B). Parse passes.
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/std_orders.sql`
**COMMIT:** `git commit -m "feat(std): rename total_tax_amount→vat_amount in std_orders (R5 std layer)"`

Wave A is now independently shippable. All three std-layer changes are committed. Proceed to Wave B when ready to deploy the full cascade.

---

## WAVE B — Published-mart cascade (coordinated deploy window)

All Wave B steps execute in a single maintenance window. Do not partially deploy Wave B.

**Pre-flight checklist:**
- [ ] Wave A all three commits applied and green
- [ ] Parquet baseline `pre_p1.txt` captured (from pre-Wave A)
- [ ] Confirm Metabase is running (will be stopped in Step 1.B6)
- [ ] Identify all blueprint files to update (grep commands in each step)

---

### STEP 1.B1 — `fact_orders`: R4 (`discount_nature → discount_type`) + R5 (`tax_amount → vat_amount`)

**Change — `transformation/models/marts/sales/fact_orders.sql`:**

R4:
- Line containing `END AS discount_nature` → `END AS discount_type`
- Line containing `MAX_BY(discount_nature, amount) AS primary_discount_nature` → `MAX_BY(discount_type, amount) AS primary_discount_type`
- Line containing `dos.primary_discount_nature,` → `dos.primary_discount_type,`

R5:
- Line containing `COALESCE(total_tax_amount, 0) as net_revenue` → `COALESCE(vat_amount, 0) as net_revenue` (the source ref `total_tax_amount` was renamed to `vat_amount` in std_orders Step 1.A3)
- Line containing `total_tax_amount as tax_amount,` → `vat_amount,` (output column renamed from `tax_amount` to `vat_amount`)

**Scope guard:**
```bash
# Verify no cost_type string labels are accidentally touched
grep -n "tax_vat\|tax_pit\|shopee" transformation/models/marts/sales/fact_orders.sql
# These must remain unchanged
```

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Strategy A
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_orders --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# T3 checksum fact_orders — row count must match pre_p1.txt; checksum will differ (column renamed) — recalculate using new column name vat_amount and compare value to old tax_amount checksum
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**Parquet value-equivalence check:**
```python
# Confirm vat_amount values = former tax_amount values (same data, new name)
import duckdb, glob, os
folder = r"app_data\data_lake\export\marts\rolling\fact_orders"
newest = sorted(glob.glob(os.path.join(folder, "*.parquet")))[-1]
print(duckdb.query(f"SELECT COUNT(*) AS n, SUM(vat_amount) AS total_vat FROM read_parquet('{newest}')").df())
# Compare total_vat to pre-rename total of tax_amount column (from pre_p1.txt baseline)
```

**PASS:** exits 0; row count matches; `SUM(vat_amount)` equals pre-rename `SUM(tax_amount)`; `discount_type` column exists with correct values.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/fact_orders.sql`; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(fact_orders): R4 discount_nature→discount_type, R5 tax_amount→vat_amount"`

---

### STEP 1.B2 — `fact_sales`: R2 (`item_id → order_line_id`), R5 (vat_amount ratio), R6 (`sol_timestamp → ordered_at`)

**Change — `transformation/models/marts/sales/fact_sales.sql`:**
- R2: `i.item_id,` → `i.order_line_id,` (the column now comes from `std_order_items` which already aliases it)
- R5: wherever `o.total_tax_amount` is used in a ratio calculation → `o.vat_amount`
- R6: `o.created_at as sol_timestamp,` → `o.created_at as ordered_at,`

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Strategy A
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_sales --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# T3 checksum for fact_sales — row count must match; verify order_line_id + ordered_at exist in parquet
python -c "import duckdb,glob,os; f=sorted(glob.glob(r'app_data\data_lake\export\marts\rolling\fact_sales\*.parquet'))[-1]; print(duckdb.query(f'SELECT COUNT(*),SUM(gross_revenue) FROM read_parquet(\"{f}\")').df())"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; row count matches; `SUM(gross_revenue)` unchanged; `order_line_id` and `ordered_at` columns present.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/fact_sales.sql`; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(fact_sales): R2 item_id→order_line_id, R5 vat_amount, R6 sol_timestamp→ordered_at"`

---

### STEP 1.B3 — `fact_order_costs`: R4 (`discount_nature → discount_type`)

**Change — `transformation/models/marts/sales/fact_order_costs.sql`:**
- `END AS discount_nature,` → `END AS discount_type,`
- `MAX_BY(discount_nature, amount) AS discount_nature,` → `MAX_BY(discount_type, amount) AS discount_type,`
- All `NULL AS discount_nature,` occurrences → `NULL AS discount_type,`

Verify count of changes:
```bash
grep -c "discount_nature" transformation/models/marts/sales/fact_order_costs.sql
# Should return 0 after edit
```

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Strategy A
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_order_costs --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 checksum for fact_order_costs — row count must match pre_p1.txt
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** exits 0; row count matches; `discount_type` column present; zero `discount_nature` refs remain.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/fact_order_costs.sql`; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(fact_order_costs): R4 discount_nature→discount_type"`

---

### STEP 1.B4 — Downstream consumers: `fact_order_economics` (R5), `mart_sku_economics_monthly` (R6), `int_us_shipment_line_prices` (R2), `dim_products` (R3)

Four small-blast-radius models, batched in one build:

**Changes:**

`fact_order_economics.sql`:
- CTE select from `fact_orders`: `tax_amount,` → `vat_amount,` (since `fact_orders` now outputs `vat_amount`)
- Final SELECT: `o.tax_amount,` → `o.vat_amount,`

`mart_sku_economics_monthly.sql`:
- `DATE_TRUNC('month', fs.sol_timestamp)` → `DATE_TRUNC('month', fs.ordered_at)`
- `DATE(fs.sol_timestamp)` → `DATE(fs.ordered_at)`
- `WHERE fs.sol_timestamp >= ...` → `WHERE fs.ordered_at >= ...`

`int_us_shipment_line_prices.sql`:
- All `item_id` references → `order_line_id` (lines 9, 31, 49, 69 — scan full file; update PARTITION BY too)

`dim_products.sql` (R3):
- All `AS is_active_status` → `AS is_active` (3 locations: catalog_final, fallback_variants, Unknown sentinel)
- Update any comment referencing `is_active_status`

**Checkpoint:**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Strategy A
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_order_economics mart_sku_economics_monthly int_us_shipment_line_prices dim_products --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# T3 checksums for fact_order_economics + dim_products — row counts match pre_p1.txt
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```

**PASS:** all four build; `dim_products` row count matches; `fact_order_economics` `vat_amount` column present.
**ROLLBACK:** `git checkout --` the four changed files; Strategy A rebuild.
**COMMIT:** `git commit -m "feat(marts): R2/R3/R5/R6 cascade — fact_order_economics, mart_sku_economics_monthly, int_us_shipment_line_prices, dim_products"`

---

### STEP 1.B5 — `dim_customers` + `dim_customers_base`: verify R1 propagation

**Change:** Read `dim_customers.sql` and `dim_customers_base.sql`. If either selects `total_expense` from `std_customers`, rename to `total_spend`. If neither does (likely — they use `monetary_value` from `int_customer_metrics`), no edit is needed.

**Verification (read-only, no build if no change):**
```bash
grep -n "total_expense\|total_spend" transformation/models/marts/core/dim_customers.sql transformation/models/marts/core/dim_customers_base.sql
```

If grep returns matches → edit + build `dim_customers dim_customers_base` using Strategy A.
If no matches → document "R1 is std-only confirmed" and proceed.

**COMMIT (conditional):** `git commit -m "feat(dim_customers): R1 propagation confirmed [no-op|renamed]"`

---

### STEP 1.B6 — Serving rebuild (T8)

Stop Metabase, rebuild serving views, restart. Required because published columns were renamed.

```bash
docker compose stop metabase
python scripts/provisioning/bootstrap_serving_views.py
# Inspect output — must contain no "Error" or "binder" lines
docker compose start metabase
```

**Checkpoint:**
```bash
# Verify olap.duckdb reflects new column names
docker exec data_platform sh -c "duckdb /app/var/olap.duckdb -c 'SELECT vat_amount FROM fact_orders LIMIT 1' 2>&1"
docker exec data_platform sh -c "duckdb /app/var/olap.duckdb -c 'SELECT discount_type FROM fact_orders LIMIT 1' 2>&1"
docker exec data_platform sh -c "duckdb /app/var/olap.duckdb -c 'SELECT is_active FROM dim_products LIMIT 1' 2>&1"
```

**PASS:** all three queries return a row without error.
**ROLLBACK:** revert all Wave B mart SQL edits (Steps 1.B1–1.B5); re-run `bootstrap_serving_views.py`; restart Metabase.

---

### STEP 1.B7 — detailView code updates + image rebuild (T9)

**Changes (all in one edit batch):**

`order_mappers.py`:
- `row.get("tax_amount")` → `row.get("vat_amount")` (R5)
- `row.get("primary_discount_nature")` → `row.get("primary_discount_type")` (R4)
- `row.get("discount_nature")` → `row.get("discount_type")` (R4)

`queries/order_header.sql`:
- `fo.tax_amount,` → `fo.vat_amount,` (R5)
- `fo.primary_discount_nature,` → `fo.primary_discount_type,` (R4)

`queries/order_line_items.sql`:
- `fs.item_id,` → `fs.order_line_id,` (R2)

`queries/order_costs.sql`:
- `discount_nature,` → `discount_type,` (R4)

`domain/order.py`:
- `OrderFinancial.tax_amount` field → `vat_amount` (R5)
- `ChannelInfo.primary_discount_nature` field → `primary_discount_type` (R4)
- `CostRow.discount_nature` field → `discount_type` (R4)
- `LineItem.item_id` field → `order_line_id` (R2)

Templates: `grep -rn "tax_amount\|discount_nature\|item_id" detailView/app/web/templates/` and update display labels.

**Rebuild image (T9):**
```bash
docker compose up -d --build detail_view
```

**Checkpoint:**
```bash
# Wait ~30s for container to start, then smoke test
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<any_valid_order_code>/tab/financial
# Must return 200
curl -s http://localhost:8000/orders/<any_valid_order_code>/tab/financial | grep -i "vat\|discount_type\|order_line"
```

**PASS:** HTTP 200; financial tab renders; no 500 errors in container logs.
**ROLLBACK:** `git checkout -- detailView/`; `docker compose up -d --build detail_view`.
**COMMIT:** `git commit -m "feat(detailView): R2/R4/R5 — order_line_id, discount_type, vat_amount"`

---

### STEP 1.B8 — Blueprint updates + redeploy

**Identify affected blueprints:**
```bash
grep -rl "tax_amount\|discount_nature\|primary_discount_nature\|sol_timestamp\|item_id\|is_active_status\|total_expense" docs/analytics-handbook/blueprints/
```

**For each blueprint file returned:**
- R5: `tax_amount` → `vat_amount` (only where referencing Sapo VAT; leave `vat_tax` Shopee column untouched)
- R4: `discount_nature` / `primary_discount_nature` → `discount_type` / `primary_discount_type`
- R6: `sol_timestamp` → `ordered_at`
- R2: `item_id` → `order_line_id`
- R3: `is_active_status` → `is_active`
- R1: `total_expense` → `total_spend`

**Post-edit verification:**
```bash
# Must return zero lines
grep -r "tax_amount\|discount_nature\|primary_discount_nature\|sol_timestamp\b\|\.item_id\b\|is_active_status\|total_expense" docs/analytics-handbook/blueprints/
```

**Redeploy affected blueprints:**
```bash
# For each affected blueprint:
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/<blueprint>.md
```

**Checkpoint:**
- Open each redeployed dashboard in Metabase browser; confirm no "unknown column" errors.
- Spot-check `order_listing` for `vat_amount` and `discount_type` columns.

**PASS:** All dashboard cards load; zero "unknown column" errors; post-edit grep returns zero.
**ROLLBACK:** `git checkout -- docs/analytics-handbook/blueprints/`; redeploy previous versions.
**COMMIT:** `git commit -m "feat(blueprints): R1/R2/R3/R4/R5/R6 column renames in all affected blueprints"`

---

### STEP 1.B9 — Full post-deploy harness validation

**T3 — parquet checksums (all affected marts):**
Run T3 against `fact_orders, fact_order_costs, fact_order_economics, fact_sales, dim_products, mart_sku_economics_monthly`.
Save to `snapshots/post_p1.txt`.

For each mart:
- **Row count** must match `pre_p1.txt` exactly.
- **Value checksum** on renamed columns: recalculate using new column name and assert equal to pre-rename checksum computed on old name (proves data unchanged, only alias changed).

**T4 — Dagster green run:**
```bash
docker exec data_platform sh -c "dagster run list --limit 3"
docker logs data_platform --since 10m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**T7 — App smoke:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<valid_code>/tab/financial
```

**PASS (all required):**
- All mart row counts match pre_p1.txt
- All mart value checksums match (renamed columns carry identical values)
- Dagster realtime job: RUN_SUCCESS
- detailView: HTTP 200

---

## Success criteria

- `dbt build` clean after each step (zero errors, zero test failures)
- Harness: row counts identical; key-column values identical (names changed, data unchanged)
- Metabase: no broken queries; renamed columns display correct values
- detailView: order detail renders `vat_amount`, `order_line_id`, `primary_discount_type` correctly
- Post-deploy grep: zero remaining old names in blueprints and SQL

---

## Rollback plan

**Wave A rollback:** revert 3 std model edits + schema.yml; `dbt build --select tag:standard`. ~5 min.

**Wave B rollback:** revert all mart SQL + detailView code; Strategy A rebuild for affected DAG; stop Metabase → `bootstrap_serving_views.py` → start Metabase; rebuild detailView image; redeploy previous blueprint versions. ~45 min. **Do not attempt partial Wave B rollback** — column mismatches between marts cause silent join failures.

---

## Next steps
After P1 harness passes: Phase 2 (P2 consistency renames — `_timestamp→_at`, `order_count`, `net_revenue`). Largest blast radius: `order_timestamp` in 24 blueprint files.

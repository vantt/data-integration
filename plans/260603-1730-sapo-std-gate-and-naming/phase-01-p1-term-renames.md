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
- Layer conventions: `docs/architecture/std-layer-conventions.md`
- Verification toolkit: `plans/260603-1730-sapo-std-gate-and-naming/verification-protocol.md`
- Blocked by: Phase 0 complete

---

## Overview
- **Priority:** P1 — semantically wrong names must not bake into the v3 contract
- **Status:** pending — blocked by Phase 0
- **Lock strategy:** Strategy A (Dagster UI pause, not CLI — CLI is ineffective on this daemon; see verification-protocol.md Lock-Handling Guidance) for all `dbt build` steps. Parse is lock-free.
- **Structure:** Tier 1 (1 std-internal step, batch OK) + Tier 2 (5 per-column atomic cascades, ordered by blast radius). Each column = one independently shippable + revertible commit.

---

## Cross-cutting addendum (resolved 2026-06-03)

**A THIRD published consumer — Rill.** Besides Metabase + detailView, the **Rill** serving layer (`rill` container, port 3002) reads mart parquet via `rill/models/*.sql`. Renaming a published column breaks the Rill model until updated. Affected:
- `tax_amount→vat_amount` (2d): update `rill/models/orders_enriched.sql`.
- `item_id→order_line_id` (2c): update `rill/models/sales_items_enriched.sql`.
- `sol_timestamp→ordered_at` (2e): update `rill/models/sales_items_enriched.sql`.
- `discount_*`, `is_active_status`, `total_expense`: NOT in Rill — no impact.

For each affected column, ADD a Rill stage to the cutover (after serving rebuild + blueprint deploy): edit `rill/models/*.sql` → new name, then `python scripts/provisioning/publish_rill_assets.py`, then `docker compose restart rill`; verify Rill (port 3002) loads.

**Q1 resolved — detailView test fixture IS a column ref.** `detailView/tests/test_shipment_search.py:109` declares `tax_amount DECIMAL(18,2)` in a CREATE TABLE fixture → update it in step 2d.

**Q3 resolved — stg schema.yml stays.** `transformation/models/staging/schema.yml` keeps `item_id` and other source names. Per std-layer conventions R2/R3, **stg is source-faithful**; the rename happens at the std layer (`std_order_items`), NOT stg. Do NOT edit stg schema.yml in step 2c.

---

## Rename table

| # | Current | New | Tier |
|---|---------|-----|------|
| R1 | `total_expense` | `total_spend` | 1 (std-internal) |
| R4 | `discount_nature` / `primary_discount_nature` | `discount_type` / `primary_discount_type` | 2a |
| R3 | `is_active_status` | `is_active` | 2b |
| R2 | `item_id` | `order_line_id` | 2c |
| R5 | `total_tax_amount` / `tax_amount` | `vat_amount` | 2d |
| R6 | `sol_timestamp` | `ordered_at` | 2e (last — largest blast) |

**DO NOT rename `order_code → order_number`.** Alphanumeric; `_number` misleads. See naming-conventions.md §2.

**R5 SCOPE GUARD:** rename ONLY the Sapo embedded VAT column (`total_tax_amount` in `std_orders` / `tax_amount` in `fact_orders`). Do NOT touch: cost_type label strings `'tax_vat'`/`'tax_pit'` in `fact_order_costs`; Shopee columns `vat_tax`, `personal_income_tax`; any non-Sapo tax column.

---

## GOLDEN RULE — Metabase workflow (MANDATORY, every column step)

> **Blueprint .md is the SOURCE OF TRUTH. Edit the .md FIRST. Deploy AFTER serving rebuild. Never hand-edit Metabase directly.**

Correct order for every Tier-2 column cutover:
1. Edit dbt SQL (all models).
2. Edit blueprint `.md` files. **Prepare only — do NOT deploy yet.**
3. Edit detailView source files. **Prepare only — do NOT rebuild yet.**
4. `dbt build` affected marts.
5. `docker compose stop metabase` → `python scripts/provisioning/bootstrap_serving_views.py` → `docker compose start metabase`.  
   Metabase MUST be stopped before `bootstrap_serving_views.py` — running both simultaneously causes DuckDB binder errors.
6. Deploy each edited blueprint: `node .skills/metabase-automation/scripts/deploy_from_markdown.js <blueprint.md>`.
7. If detailView touched: `docker compose up -d --build detail_view`.

---

## PRE-PHASE: Capture parquet baseline

Before touching any file, capture baseline checksums (see verification-protocol.md §T3):

```bash
python "plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py" \
  fact_orders fact_order_costs fact_order_economics fact_sales \
  dim_products dim_customers mart_sku_economics_monthly
```

Save to `snapshots/pre_p1.txt`. Lock-free — can run while pipeline is live.

---

## TIER 1 — `total_expense → total_spend` (R1, std-internal)

**Blast radius:** std-internal only. `dim_customers` / `dim_customers_base` do NOT reference `total_expense` (they pull `monetary_value` from `int_customer_metrics`). Zero blueprints. Zero detailView. Zero serving rebuild needed.

### STEP 1.1 — Edit dbt models

**Files to edit:**

| File | Change |
|------|--------|
| `transformation/models/staging/standard/std_customers.sql` | `coalesce(total_expense, 0) as total_expense` → `coalesce(total_expense, 0) as total_spend` |
| `transformation/models/staging/standard/schema.yml` | column entry `total_expense` → `total_spend` under `std_customers` |

**Scope guard — verify no propagation to published dims:**
```bash
grep -n "total_expense\|total_spend" transformation/models/marts/core/dim_customers_base.sql
grep -n "total_expense\|total_spend" transformation/models/marts/core/dim_customers.sql
# Both must return zero lines (R1 is std-only confirmed)
```

### STEP 1.2 — Build + verify

```bash
# T1 — parse
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

# Pause schedules via Dagster UI (CLI is ineffective — see verification-protocol.md R8/Lock-Handling)
# Then Strategy A manual build:
docker exec data_platform sh -c "cd /app && dbt build --select std_customers --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"

# T4 — wait for or trigger a FRESH Dagster realtime run AFTER the edit:
docker exec data_platform sh -c "dagster job launch -j ingest_sapo_realtime_job -f /app/orchestration/definitions.py"
docker logs data_platform --since 10m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**Checksum (--percol, name-agnostic):**
```bash
python "plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py" --percol std_customers
# Sorted per-column value fingerprint must match pre_p1.txt for this model
```

**PASS:** `dbt build` exits 0; fresh Dagster run `RUN_SUCCESS`; scope guard grep returns 0 lines; per-column checksum matches (values unchanged, only alias renamed).

**Rollback:** `git checkout -- transformation/models/staging/standard/std_customers.sql transformation/models/staging/standard/schema.yml`; re-parse.

**Commit:** `git commit -m "feat(std): rename total_expense→total_spend in std_customers (R1)"`

---

## TIER 2 — Per-column atomic cascades

Each step below = one atomic, independently shippable unit. Complete Tier 1 first, then execute these in order (2a→2e). You MAY stop after any column and leave the rest pending.

---

### STEP 2a — `discount_nature → discount_type` + `primary_discount_nature → primary_discount_type` (R4)

**Blast radius summary:**
- dbt: 3 files (`fact_orders.sql`, `fact_order_costs.sql`, `schema.yml`)
- Blueprints: 0 (confirmed grep — no blueprints reference `discount_nature`)
- detailView: YES — 5 files (domain, mapper, query, template, seed)

**dbt files to edit:**

| File | Change |
|------|--------|
| `transformation/models/marts/sales/fact_orders.sql` | `END AS discount_nature` → `END AS discount_type`; `MAX_BY(discount_nature, amount) AS primary_discount_nature` → `MAX_BY(discount_type, amount) AS primary_discount_type`; `dos.primary_discount_nature,` → `dos.primary_discount_type,` |
| `transformation/models/marts/sales/fact_order_costs.sql` | All `AS discount_nature` → `AS discount_type`; `MAX_BY(discount_nature, amount) AS discount_nature` → `MAX_BY(discount_type, amount) AS discount_type`; all `NULL AS discount_nature` → `NULL AS discount_type` |
| `transformation/models/marts/schema.yml` | Column entries `discount_nature` / `primary_discount_nature` → `discount_type` / `primary_discount_type` |

Verify exhaustion:
```bash
grep -c "discount_nature" transformation/models/marts/sales/fact_orders.sql transformation/models/marts/sales/fact_order_costs.sql transformation/models/marts/schema.yml
# Must all return 0
```

**Blueprint files to edit:** none (grep confirmed 0 blueprints reference `discount_nature`).

**detailView files to edit (PREPARE ONLY — do NOT rebuild yet):**

| File | Change |
|------|--------|
| `detailView/app/domain/order.py` | `ChannelInfo.primary_discount_nature` → `primary_discount_type`; `CostRow.discount_nature` → `discount_type` |
| `detailView/app/adapters/outbound/duckdb/order_mappers.py` | `row.get("primary_discount_nature")` → `row.get("primary_discount_type")`; `row.get("discount_nature")` → `row.get("discount_type")` |
| `detailView/app/adapters/outbound/duckdb/queries/order_header.sql` | `fo.primary_discount_nature,` → `fo.primary_discount_type,` |
| `detailView/app/adapters/outbound/duckdb/queries/order_costs.sql` | `discount_nature,` → `discount_type,` |
| `detailView/app/adapters/inbound/web/templates/partials/order/_channel_staff.html` | `ch.primary_discount_nature` → `ch.primary_discount_type` (2 occurrences: the `if` condition and the `append` call) |

Note: `detailView/tests/seed_schema.py` and `detailView/app/adapters/inbound/web/_demo_stub.py` also reference `discount_nature` — update these too (test/stub alignment).

**Coordinated cutover (exact order):**

1. Apply all dbt + detailView edits above.
2. `dbt parse` → must be clean.
3. Pause schedules via Dagster UI. Run Strategy A build:
   ```bash
   docker exec data_platform sh -c "cd /app && dbt build --select fact_orders fact_order_costs --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
   ```
4. Serving rebuild (Metabase must be stopped first):
   ```bash
   docker compose stop metabase
   python scripts/provisioning/bootstrap_serving_views.py
   docker compose start metabase
   ```
5. No blueprints to deploy.
6. Rebuild detailView:
   ```bash
   docker compose up -d --build detail_view
   ```
7. Resume schedules. Trigger or wait for a FRESH Dagster realtime run.

**Verify (rename gate):**
- **Primary:** code review — diff is a pure rename, no logic change.
- `dbt build` exits 0, `ERROR=0 FAIL=0`.
- Fresh Dagster run `RUN_SUCCESS`.
- **Best-effort checksum** (live-data drift caveat — see below):
  ```bash
  python "plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py" --percol fact_orders fact_order_costs
  ```
  Sorted per-column value fingerprints must match pre_p1.txt. If new orders arrived mid-step, whole-row checksums will drift from new data — that is expected; fall back to code-review + green tests as the gate.
- detailView smoke:
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<valid_order_code>/tab/financial
  # Must return 200
  curl -s http://localhost:8000/orders/<valid_order_code>/tab/financial | grep -i "discount_type"
  ```

**Rollback:** `git revert HEAD`; re-run `dbt build --select fact_orders fact_order_costs`; stop Metabase → `bootstrap_serving_views.py` → start Metabase; `docker compose up -d --build detail_view`.

**Commit:** `git commit -m "feat(marts,detailView): R4 discount_nature→discount_type, primary_discount_nature→primary_discount_type"`

---

### STEP 2b — `is_active_status → is_active` (R3)

**Blast radius summary:**
- dbt: 1 file (`dim_products.sql`) — 3 occurrences
- Blueprints: 0 (confirmed grep)
- detailView: NO

**dbt files to edit:**

| File | Change |
|------|--------|
| `transformation/models/marts/core/dim_products.sql` | All `AS is_active_status` → `AS is_active` (3 locations: catalog_final CTE, fallback_variants CTE, Unknown sentinel row); update any comment referencing `is_active_status` |

Verify exhaustion:
```bash
grep -c "is_active_status" transformation/models/marts/core/dim_products.sql
# Must return 0
```

**Blueprint files to edit:** none.

**detailView files to edit:** none.

**Coordinated cutover:**

1. Apply dbt edit.
2. `dbt parse` → clean.
3. Pause via Dagster UI. Strategy A build:
   ```bash
   docker exec data_platform sh -c "cd /app && dbt build --select dim_products --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
   ```
4. Serving rebuild:
   ```bash
   docker compose stop metabase
   python scripts/provisioning/bootstrap_serving_views.py
   docker compose start metabase
   ```
5. No blueprints to deploy. No detailView rebuild.
6. Resume schedules. Fresh Dagster run.

**Verify:**
- `dbt build` exits 0.
- Fresh Dagster run `RUN_SUCCESS`.
- Checksum:
  ```bash
  python "plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py" --percol dim_products
  # Per-column value fingerprint matches (same bool values, new column name)
  ```
- Serving smoke: `duckdb /app/var/olap.duckdb -c 'SELECT is_active FROM dim_products LIMIT 1'` returns a row.

**Rollback:** `git revert HEAD`; rebuild `dim_products`; stop → `bootstrap_serving_views.py` → start Metabase.

**Commit:** `git commit -m "feat(dim_products): R3 is_active_status→is_active"`

---

### STEP 2c — `item_id → order_line_id` (R2)

**Blast radius summary:**
- dbt: 4 files (`std_order_items.sql`, `schema.yml` (staging/standard), `fact_sales.sql`, `int_us_shipment_line_prices.sql`) + `schema.yml` (staging) for stg-level column doc
- Blueprints: 1 (`docs/analytics-handbook/blueprints/order_detail.md`)
- detailView: YES — 5 files (domain, mapper, query, test, seed/stub)

**dbt files to edit:**

| File | Change |
|------|--------|
| `transformation/models/staging/standard/std_order_items.sql` | `item_id,` → `item_id AS order_line_id,` |
| `transformation/models/staging/standard/schema.yml` | column entry `item_id` → `order_line_id` under `std_order_items` |
| `transformation/models/marts/sales/fact_sales.sql` | `i.item_id,` → `i.order_line_id,` |
| `transformation/models/intermediate/us_shipment/int_us_shipment_line_prices.sql` | All `item_id` references → `order_line_id` (scan full file; includes PARTITION BY clauses) |

Verify exhaustion (only in dbt pipeline files):
```bash
grep -n "\bitem_id\b" transformation/models/staging/standard/std_order_items.sql \
  transformation/models/marts/sales/fact_sales.sql \
  transformation/models/intermediate/us_shipment/int_us_shipment_line_prices.sql
# Must return 0 lines
```

**Blueprint files to edit (PREPARE ONLY):**

| File | Change |
|------|--------|
| `docs/analytics-handbook/blueprints/order_detail.md` | `item_id` → `order_line_id` (all occurrences in SQL queries) |

**detailView files to edit (PREPARE ONLY):**

| File | Change |
|------|--------|
| `detailView/app/domain/order.py` | `LineItem.item_id` field → `order_line_id` |
| `detailView/app/adapters/outbound/duckdb/order_mappers.py` | `row.get("item_id")` → `row.get("order_line_id")` |
| `detailView/app/adapters/outbound/duckdb/queries/order_line_items.sql` | `fs.item_id,` → `fs.order_line_id,` |
| `detailView/tests/seed_schema.py` | `item_id` → `order_line_id` |
| `detailView/app/adapters/inbound/web/_demo_stub.py` | `item_id` → `order_line_id` |

Note: `detailView/tests/test_order_repository.py` also references `item_id` — update to align.

**Coordinated cutover:**

1. Apply all dbt + detailView + blueprint edits.
2. `dbt parse` → clean.
3. Pause via Dagster UI. Strategy A build:
   ```bash
   docker exec data_platform sh -c "cd /app && dbt build --select std_order_items fact_sales int_us_shipment_line_prices --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
   ```
4. Serving rebuild:
   ```bash
   docker compose stop metabase
   python scripts/provisioning/bootstrap_serving_views.py
   docker compose start metabase
   ```
5. Deploy edited blueprint:
   ```bash
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/order_detail.md
   ```
6. Rebuild detailView:
   ```bash
   docker compose up -d --build detail_view
   ```
7. Resume schedules. Fresh Dagster run.

**Verify:**
- `dbt build` exits 0; `ERROR=0 FAIL=0`.
- Fresh Dagster run `RUN_SUCCESS`.
- Checksum:
  ```bash
  python "plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py" --percol fact_sales
  # Per-column fingerprint matches (live-data drift caveat applies — see checksum note below)
  ```
- Blueprint smoke: open `order_detail` dashboard in Metabase → no "unknown column" errors.
- detailView smoke:
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<valid_code>/tab/financial
  # 200
  ```

**Rollback:** `git revert HEAD`; rebuild `std_order_items fact_sales int_us_shipment_line_prices`; stop → `bootstrap_serving_views.py` → start Metabase; redeploy prior `order_detail.md` (git-revert restores the .md — re-deploy from the reverted .md); `docker compose up -d --build detail_view`.

**Commit:** `git commit -m "feat(std,marts,blueprints,detailView): R2 item_id→order_line_id"`

---

### STEP 2d — `total_tax_amount / tax_amount → vat_amount` (R5)

**Blast radius summary:**
- dbt: 5 files (`std_orders.sql`, `fact_orders.sql`, `fact_order_economics.sql`, `fact_sales.sql`, `schema.yml` (marts))
- Blueprints: 3 (`order_listing.md`, `order_detail.md`, `finance_pl.md`)
- detailView: YES — 4 files (template, domain, mapper, query) + test/seed/stub

**dbt files to edit:**

| File | Change |
|------|--------|
| `transformation/models/staging/standard/std_orders.sql` | `tax_amount as total_tax_amount,` → `tax_amount as vat_amount,` (only the output alias; leave the source column `tax_amount` on the right side of `as` unchanged since that is the raw src field) |
| `transformation/models/marts/sales/fact_orders.sql` | Source ref `total_tax_amount` → `vat_amount` (now exposed from std_orders); output alias `total_tax_amount as tax_amount` → `vat_amount` (column output renamed); scope guard: `COALESCE(total_tax_amount, 0) as net_revenue` → `COALESCE(vat_amount, 0) as net_revenue` |
| `transformation/models/marts/sales/fact_order_economics.sql` | CTE select from `fact_orders`: `tax_amount,` → `vat_amount,`; final SELECT: `o.tax_amount,` → `o.vat_amount,` |
| `transformation/models/marts/sales/fact_sales.sql` | Wherever `o.total_tax_amount` is used in a ratio calculation → `o.vat_amount` |
| `transformation/models/marts/schema.yml` | Column entry `tax_amount` → `vat_amount` under `fact_orders`; `tax_amount` → `vat_amount` under `fact_order_economics` |

Scope guard BEFORE editing `fact_orders.sql`:
```bash
grep -n "tax_vat\|tax_pit\|shopee\|personal_income_tax" transformation/models/marts/sales/fact_orders.sql
# These must NOT change — confirm they exist and leave untouched
```

Scope guard BEFORE editing `std_orders.sql`:
```bash
grep -n "tax_amount\|vat_amount" transformation/models/staging/standard/std_orders.sql
# Only touch the output alias (right side of AS), not the raw src field reference
```

Verify exhaustion:
```bash
grep -n "\btax_amount\b\|total_tax_amount" \
  transformation/models/staging/standard/std_orders.sql \
  transformation/models/marts/sales/fact_orders.sql \
  transformation/models/marts/sales/fact_order_economics.sql \
  transformation/models/marts/sales/fact_sales.sql
# Must return 0 lines (scope guard strings like 'tax_vat' are different and will not match)
```

**Blueprint files to edit (PREPARE ONLY):**

| File | Change |
|------|--------|
| `docs/analytics-handbook/blueprints/order_listing.md` | `tax_amount` → `vat_amount` (all SQL query references to Sapo VAT column) |
| `docs/analytics-handbook/blueprints/order_detail.md` | `tax_amount` → `vat_amount` |
| `docs/analytics-handbook/blueprints/finance_pl.md` | `tax_amount` → `vat_amount` |

**detailView files to edit (PREPARE ONLY):**

| File | Change |
|------|--------|
| `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html` | `tax_amount` → `vat_amount` (the VAT row display) |
| `detailView/app/domain/order.py` | `OrderFinancial.tax_amount` field → `vat_amount` |
| `detailView/app/adapters/outbound/duckdb/order_mappers.py` | `row.get("tax_amount")` → `row.get("vat_amount")` |
| `detailView/app/adapters/outbound/duckdb/queries/order_header.sql` | `fo.tax_amount,` → `fo.vat_amount,` |
| `detailView/tests/seed_schema.py` | `tax_amount` → `vat_amount` |
| `detailView/app/adapters/inbound/web/_demo_stub.py` | `tax_amount` → `vat_amount` |

Note: `detailView/tests/test_shipment_search.py` also references `tax_amount` — verify if it is a column ref or test data and update accordingly.

**Coordinated cutover:**

1. Apply all dbt + detailView + blueprint edits (edit blueprint .md files — do NOT deploy yet).
2. `dbt parse` → clean.
3. Pause via Dagster UI. Strategy A build (the full VAT cascade):
   ```bash
   docker exec data_platform sh -c "cd /app && dbt build --select std_orders fact_orders fact_order_economics fact_sales --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -20"
   ```
4. Serving rebuild:
   ```bash
   docker compose stop metabase
   python scripts/provisioning/bootstrap_serving_views.py
   docker compose start metabase
   ```
5. Deploy edited blueprints (after serving is up — blueprint deploys connect to live Metabase):
   ```bash
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/order_listing.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/order_detail.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/finance_pl.md
   ```
6. Rebuild detailView:
   ```bash
   docker compose up -d --build detail_view
   ```
7. Resume schedules. Fresh Dagster run.

**Verify:**
- `dbt build` exits 0; `ERROR=0 FAIL=0`.
- Fresh Dagster run `RUN_SUCCESS`.
- Checksum (name-agnostic, live-data caveat applies):
  ```bash
  python "plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py" --percol fact_orders fact_order_economics fact_sales
  # Per-column value fingerprints must match pre_p1.txt
  # If rows arrived mid-step, whole-row checksums will drift — that is expected from new data, NOT the rename
  # Fall back to: code-review diff confirms pure rename + green tests
  ```
- Value sanity (run on host parquet):
  ```python
  import duckdb, glob, os
  folder = r"app_data\data_lake\export\marts\rolling\fact_orders"
  newest = sorted(glob.glob(os.path.join(folder, "*.parquet")))[-1]
  print(duckdb.query(f"SELECT COUNT(*) AS n, SUM(vat_amount) AS total_vat FROM read_parquet('{newest}')").df())
  # Compare total_vat to pre-rename SUM(tax_amount) captured in pre_p1.txt
  ```
- Blueprint smoke: open `order_listing`, `order_detail`, `finance_pl` dashboards → no "unknown column".
- detailView smoke:
  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/orders/<valid_code>/tab/financial
  # 200
  curl -s http://localhost:8000/orders/<valid_code>/tab/financial | grep -i "vat"
  # VAT row renders
  ```

**Rollback:** `git revert HEAD`; rebuild `std_orders fact_orders fact_order_economics fact_sales`; stop → `bootstrap_serving_views.py` → start Metabase; redeploy each blueprint from reverted .md; `docker compose up -d --build detail_view`.

**Commit:** `git commit -m "feat(std,marts,blueprints,detailView): R5 tax_amount/total_tax_amount→vat_amount"`

---

### STEP 2e — `sol_timestamp → ordered_at` (R6) [LARGEST BLAST — do last]

**Blast radius summary:**
- dbt: 2 files (`fact_sales.sql`, `mart_sku_economics_monthly.sql`)
- Blueprints: 7 (`sales_yesterday_operation.md`, `sales_promotion_analysis.md`, `sales_monthly_review.md`, `sales_daily_operation.md`, `marketing_weekly_tracker.md`, `marketing_monthly_analysis.md`, `ceo_monthly_scorecard.md`)
- detailView: NO (sol_timestamp not found in detailView)

**dbt files to edit:**

| File | Change |
|------|--------|
| `transformation/models/marts/sales/fact_sales.sql` | `o.created_at as sol_timestamp,` → `o.created_at as ordered_at,` |
| `transformation/models/marts/sales/mart_sku_economics_monthly.sql` | All `fs.sol_timestamp` references → `fs.ordered_at` (DATE_TRUNC, DATE(), WHERE clauses — scan full file) |

Verify exhaustion:
```bash
grep -c "sol_timestamp" transformation/models/marts/sales/fact_sales.sql transformation/models/marts/sales/mart_sku_economics_monthly.sql
# Must both return 0
```

**Blueprint files to edit (PREPARE ONLY — 7 files):**

| File | Change |
|------|--------|
| `docs/analytics-handbook/blueprints/sales_yesterday_operation.md` | `sol_timestamp` → `ordered_at` |
| `docs/analytics-handbook/blueprints/sales_promotion_analysis.md` | `sol_timestamp` → `ordered_at` |
| `docs/analytics-handbook/blueprints/sales_monthly_review.md` | `sol_timestamp` → `ordered_at` |
| `docs/analytics-handbook/blueprints/sales_daily_operation.md` | `sol_timestamp` → `ordered_at` |
| `docs/analytics-handbook/blueprints/marketing_weekly_tracker.md` | `sol_timestamp` → `ordered_at` |
| `docs/analytics-handbook/blueprints/marketing_monthly_analysis.md` | `sol_timestamp` → `ordered_at` |
| `docs/analytics-handbook/blueprints/ceo_monthly_scorecard.md` | `sol_timestamp` → `ordered_at` |

Post-edit grep — must return zero:
```bash
grep -r "sol_timestamp" docs/analytics-handbook/blueprints/
```

**detailView files to edit:** none.

**Coordinated cutover:**

1. Apply all dbt + blueprint edits.
2. `dbt parse` → clean.
3. Pause via Dagster UI. Strategy A build:
   ```bash
   docker exec data_platform sh -c "cd /app && dbt build --select fact_sales mart_sku_economics_monthly --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
   ```
4. Serving rebuild:
   ```bash
   docker compose stop metabase
   python scripts/provisioning/bootstrap_serving_views.py
   docker compose start metabase
   ```
5. Deploy all 7 blueprints (blueprint .md FIRST, then deploy — never hand-edit Metabase):
   ```bash
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/sales_yesterday_operation.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/sales_promotion_analysis.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/sales_monthly_review.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/sales_daily_operation.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/marketing_weekly_tracker.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/marketing_monthly_analysis.md
   node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/ceo_monthly_scorecard.md
   ```
6. No detailView rebuild needed.
7. Resume schedules. Fresh Dagster run.

**Verify:**
- `dbt build` exits 0; `ERROR=0 FAIL=0`.
- Fresh Dagster run `RUN_SUCCESS`.
- Checksum:
  ```bash
  python "plans/260603-1730-sapo-std-gate-and-naming/snapshots/checksum.py" --percol fact_sales mart_sku_economics_monthly
  # Per-column value fingerprint matches. Live-data drift caveat applies.
  ```
- Blueprint smoke: open each of the 7 deployed dashboards in Metabase → no "unknown column"; spot-check a date filter using `ordered_at`.
- Post-deploy grep: `grep -r "sol_timestamp" docs/analytics-handbook/blueprints/` must return zero.

**Rollback:** `git revert HEAD`; rebuild `fact_sales mart_sku_economics_monthly`; stop → `bootstrap_serving_views.py` → start Metabase; redeploy all 7 blueprints from reverted .md.

**Commit:** `git commit -m "feat(marts,blueprints): R6 sol_timestamp→ordered_at (7 blueprints)"`

---

## Checksum gate — live-data drift caveat

> The `--percol` flag computes a name-agnostic per-column sorted value fingerprint (multiset). For a pure rename, the fingerprint of the new column MUST equal the fingerprint of the old column — if only the name changed, the value multiset is identical. Use this as the rename proof.
>
> **Whole-row checksums (without --percol) WILL drift** whenever new orders arrive between the pre and post snapshots (the pipeline runs every 3 min). This is expected from live data ingestion, not from the rename. For rename steps, ALWAYS use `--percol` and rely on code-review of the diff + green tests as the primary gate if ingestion raced mid-step.

---

## Success criteria

- `dbt build` clean after each column step (zero errors, zero test failures)
- Fresh Dagster realtime run `RUN_SUCCESS` after each column step
- Per-column value checksums (`--percol`) match between pre and post for all renamed columns
- Metabase: no "unknown column" on any deployed dashboard
- detailView (where touched): Financial tab renders `vat_amount`, `discount_type`, `order_line_id` correctly
- Post-deploy grep: zero old names remaining in blueprints and pipeline SQL

---

## Rollback plan

**Per-column rollback (independent):** `git revert HEAD` for that column's commit → re-run `dbt build` for affected models → stop Metabase → `bootstrap_serving_views.py` → start Metabase → redeploy blueprint(s) from reverted .md → `docker compose up -d --build detail_view` (if detailView was touched). ~10-20 min per column. Each column is independently revertible; reverting one does not cascade to others.

**Tier 1 rollback:** `git checkout -- std_customers.sql schema.yml`; re-parse. ~2 min.

---

## Next steps

After P1 harness passes: Phase 2 (P2 consistency renames — `_timestamp→_at`, `order_count`, `net_revenue`). Largest blast radius in Phase 2: `order_timestamp` in 24 blueprint files.

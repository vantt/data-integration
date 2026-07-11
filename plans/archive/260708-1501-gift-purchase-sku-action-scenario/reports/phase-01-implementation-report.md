# Phase 1 Implementation Report — Gift Line Classification

Plan: `plans/260708-1501-gift-purchase-sku-action-scenario/phase-01-gift-line-classification.md`
Date: 2026-07-08

## What Changed

1. `transformation/models/staging/standard/std_order_items.sql:32` — added `(line_amount = 0) AS is_gift_line,` directly after `line_amount` in the SELECT list.
2. `transformation/models/marts/sales/fact_sales.sql:81` — added `i.is_gift_line,` pass-through alongside `i.discount_amount`/`i.distributed_discount_amount`/`i.discount_rate`.
3. `transformation/models/staging/standard/schema.yml:60-62` — added `is_gift_line` doc string + `not_null` test under `std_order_items`.
4. `transformation/models/marts/schema.yml:842-844` — added `is_gift_line` doc string + `not_null` test under `fact_sales`.

No other lines touched in any of the four files (verified via `git diff`).

## NULL-guard decision (bare equality vs COALESCE)

Phase file flagged verifying whether `line_amount` can be NULL before choosing bare `= 0` vs `COALESCE(line_amount, -1) = 0`. Verified empirically against the live warehouse (`main_staging.std_order_items`, 27,687 rows): `COUNT(*) FILTER (WHERE line_amount IS NULL) = 0`. Cross-checked via `fact_sales.net_revenue` (derived from `line_amount`) — also 0 NULLs. Used bare `line_amount = 0` as written in the phase's exact snippet; no COALESCE guard needed. The new `not_null` dbt test on `is_gift_line` now acts as a permanent regression guard if this assumption ever breaks.

## dbt Run

Restarted `data_platform` (manifest reload), then:
```
dbt run --select std_order_items fact_sales
```
Result: `PASS=2 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=2` — both models rebuilt successfully.

```
dbt test --select std_order_items fact_sales
```
Result: `PASS=19 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=19`, including the two new tests:
- `not_null_std_order_items_is_gift_line` — PASS
- `not_null_fact_sales_is_gift_line` — PASS

## Row-Count Regression Check

- `main_marts.fact_sales` count before dbt run: 27,687
- `main_marts.fact_sales` count after dbt run: 27,687
- No regression.

## is_gift_line NULL Check (fact_sales)

`COUNT(*) FILTER (WHERE is_gift_line IS NULL)` = 0 (27,687 total rows). Distribution: `is_gift_line=FALSE` → 15,552 rows; `is_gift_line=TRUE` → 12,135 rows.

## Verification Query (corrected, per phase file §5)

Ran the `fs_resolved`/`fs_agg` cross-check against `main.int_order_promo_goods_cost.line_revenue = 0` (note: this intermediate model lives in the `main` schema, not `main_marts` — resolved via `information_schema.tables` lookup, not otherwise a deviation):

```sql
WHERE a.all_lines_gift = FALSE AND p.line_revenue = 0
```

Result: **0 disagreements** — matches expected outcome. `is_gift_line` (line-item grain) and `int_order_promo_goods_cost.line_revenue = 0` (order_code×sku grain SUM) agree everywhere they overlap.

## Success Criteria (from phase file)

- [x] `std_order_items.is_gift_line` exists, `line_amount = 0` test, documented in schema.yml
- [x] `fact_sales.is_gift_line` pass-through, no NULL values where `line_amount` is populated (0 NULLs, all 27,687 rows populated)
- [x] Cross-check query against `int_order_promo_goods_cost.line_revenue = 0` returns 0 disagreements
- [x] `dbt run --select std_order_items fact_sales` succeeds, no regression in row counts (27,687 → 27,687)
- [x] Existing `discount_rate`/`discount_amount`/`distributed_discount_amount` columns unchanged (confirmed via `git diff` — no lines touched)

## Deviations From Phase File

None in design/SQL. Two operational notes not specified in the phase file (neither is a deviation from the spec, just execution detail):
- `int_order_promo_goods_cost` resolves to schema `main`, not `main_marts`, in the raw warehouse DB — used `main.int_order_promo_goods_cost` in the ad-hoc verification query.
- Warehouse DB (`sapo_warehouse.duckdb`) was transiently write-locked by another process on first read-only connection attempt (single-writer DuckDB); retried moments later and it succeeded — no code or config change made, purely a query-timing note.

## Files Modified

- `transformation/models/staging/standard/std_order_items.sql` (+2/-1 lines)
- `transformation/models/marts/sales/fact_sales.sql` (+1 line)
- `transformation/models/staging/standard/schema.yml` (+3 lines)
- `transformation/models/marts/schema.yml` (+3 lines)

## Unresolved Questions

None.

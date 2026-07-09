# Plan: Overhead Budgeted-Rate Branch for Open Months

**Created:** 2026-06-09  
**Status:** SUPERSEDED (2026-07-08) — goal achieved via a different mechanism, this plan's specific approach was never built
**Priority:** Medium — P4-3 from `260604-1030-unified-order-pl-cogs-overhead`

## Superseded — resolution note (2026-07-08)

The open-month overhead gap this plan targeted is **fixed in production**, but not via
`budgeted_rate`/gsheet as designed here. `overhead_allocation_config` was found to not exist
(no gsheet, no `budgeted_rate` column — see
`plans/archive/reports/scout-260605-2155-p4-3-provisional-overhead.md`). Instead
`int_order_overhead_allocation.sql` (in `plans/archive/260604-1030-unified-order-pl-cogs-overhead/`)
implements a UNION of:
- **ACTUAL branch** — closed months (`period_month < current ICT month`), pro-rata from MISA actual pool, `is_overhead_estimated = FALSE`.
- **ESTIMATED branch** — current/open month, trailing 3-closed-month rate per pool, `is_overhead_estimated = TRUE`.

Verified wired end-to-end: `fact_order_economics.is_overhead_estimated` (BOOL_OR from allocation),
`fact_order_costs.fee_source = 'estimated'|'actual'`, and
`assert_overhead_allocation_closure.sql` scoped to closed months only. Auto true-up on MISA
arrival confirmed by design (full-rebuild pipeline, no restate logic needed).

This plan's UNION-in-`int_overhead_pool_monthly` design (Steps 1-2) and gsheet `budgeted_rate`
column were never implemented and should not be — the trailing-rate approach is the shipped
solution. Keeping this file for historical record only.

## Problem

`int_overhead_pool_monthly` reads only from `std_misa_account_ledger`. For the current open month (MISA not yet closed), no rows exist → `allocated_overhead = NULL` in all of `fact_order_economics`. Dashboard P&L shows no overhead for the running month.

**Goal:** When MISA data is absent for a month, fall back to `budgeted_rate` from `overhead_allocation_config` gsheet to estimate the pool. Set `is_overhead_estimated = TRUE` for these rows. When MISA data later arrives and the pipeline re-runs, actual data takes over automatically (true-up).

## Scope

| Layer | File | Change |
|---|---|---|
| Source config | `overhead_allocation_config` gsheet | Add `budgeted_rate` column (if not present) |
| Staging | `stg_overhead_account_classification.sql` | No change needed (classification only) |
| Intermediate | `int_overhead_pool_monthly.sql` | Add UNION branch for open months |
| Intermediate | `int_order_overhead_allocation.sql` | Propagate `is_estimated` flag |
| Mart | `fact_order_economics.sql` | Already has `is_overhead_estimated` column |
| Mart | `fact_order_costs.sql` | Already has `is_estimated` + `source_system='gsheet'` fields |
| Schema | `schema.yml` | Add test: `is_overhead_estimated` not_null for recent months |

## Architecture

```
overhead_allocation_config (gsheet)
    └── budgeted_rate per pool_id
            │
            ▼
int_overhead_pool_monthly
    ├── ACTUAL branch:  MISA data exists for period_month
    │       pool_net = SUM(net_cost), is_estimated = FALSE
    └── BUDGETED branch: no MISA data for period_month
            pool_net = budgeted_rate, is_estimated = TRUE
    └─► UNION → grain: (pool_id, base_metric, period_month, pool_net, is_estimated)
```

**Key rule:** Actual branch takes precedence. If MISA row exists for a (pool_id, period_month), the budgeted branch is excluded for that period. Anti-join pattern.

## Implementation Steps

### Step 1 — Verify gsheet schema
- Check `overhead_allocation_config` source table has `budgeted_rate` column
- If missing: add to gsheet + update `sources.yml` definition

### Step 2 — Modify `int_overhead_pool_monthly.sql`
Add budgeted fallback via anti-join:

```sql
-- Months that have ACTUAL MISA data (closed months)
actual_pools AS (
    SELECT pool_id, base_metric, period_month,
           SUM(net_cost) AS pool_net,
           FALSE AS is_estimated
    FROM ledger_classified
    GROUP BY pool_id, base_metric, period_month
),

-- Budgeted fallback: only for pool×month combos NOT in actual_pools
-- Source: overhead_allocation_config.budgeted_rate × 1 (flat monthly amount)
budgeted_pools AS (
    SELECT
        c.pool_id,
        c.base_metric,
        gs.period_month,
        c.budgeted_rate AS pool_net,
        TRUE AS is_estimated
    FROM {{ ref('stg_overhead_allocation_config') }} c
    CROSS JOIN (
        -- Generate months from config effective_from to current month
        SELECT DATE_TRUNC('month', CURRENT_DATE) AS period_month
    ) gs
    WHERE c.budgeted_rate IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM actual_pools ap
          WHERE ap.pool_id = c.pool_id
            AND ap.period_month = gs.period_month
      )
)

SELECT * FROM actual_pools
UNION ALL
SELECT * FROM budgeted_pools
```

> Note: `gs` subquery generates only current month for v1. Can extend to future months later.

### Step 3 — Verify `int_order_overhead_allocation.sql`
- Confirm `is_estimated` propagates from pool to order-level rows
- If not present: add `BOOL_OR(p.is_estimated) AS is_overhead_estimated` in aggregation

### Step 4 — Simulate open month (test)
Two options:
- **Option A (preferred):** Temporarily add a row to `overhead_allocation_config` gsheet with `budgeted_rate` for the current month (before MISA data arrives). Run `dbt build --select +fact_order_economics`. Verify `is_overhead_estimated = TRUE` for current-month orders and `allocated_overhead IS NOT NULL`.
- **Option B (offline):** Add a test fixture month (e.g., `2099-01-01`) with `budgeted_rate` to a seed file, run the intermediate models in isolation.

### Step 5 — Real Dagster run
After simulation passes: trigger full `sapo_dbt_assets` materialization. Verify in Dagster logs and query `fact_order_economics` for current month.

### Step 6 — Cleanup
- Remove test fixture if Option B used
- Update `phase-04-overhead-allocation.md` P4-3 → checked

## Todo

- [ ] Step 1: verify `overhead_allocation_config` gsheet has `budgeted_rate` column
- [ ] Step 2: modify `int_overhead_pool_monthly.sql` — add UNION budgeted branch
- [ ] Step 3: verify `is_estimated` propagation in `int_order_overhead_allocation.sql`
- [ ] Step 4: simulate open month (Option A preferred)
- [ ] Step 5: real Dagster run — end-to-end verification
- [ ] Step 6: cleanup + mark P4-3 done in parent plan

## Success Criteria

1. Current-month orders have `allocated_overhead IS NOT NULL` and `is_overhead_estimated = TRUE`
2. Previous closed months still have `is_overhead_estimated = FALSE`
3. After MISA data ingested for the month, re-run flips to `FALSE` (true-up)
4. `SUM(allocated_overhead)` for the month ≈ `budgeted_rate` (within rounding)
5. Dagster run completes with no errors

## Dependencies

- `overhead_allocation_config` gsheet must have `budgeted_rate` per pool populated
- Requires knowing what a reasonable budgeted monthly overhead is (business input)

## Deferred

- Multi-month budgeted projection (future months beyond current)
- Pool-level budgeted rates (v1 uses one flat rate per pool)

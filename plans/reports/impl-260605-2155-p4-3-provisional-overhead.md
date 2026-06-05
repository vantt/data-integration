# Implementation Report: P4-3 Provisional Overhead Estimate

**Date:** 2026-06-05 | **Task:** Phase-04 P4-3 (Q4-B) | **Status:** DONE_WITH_CONCERNS

---

## Files Modified

| File | Change |
|---|---|
| `transformation/models/intermediate/overhead/int_order_overhead_allocation.sql` | Added UNION estimate branch; scoped actual branch to closed months |
| `transformation/tests/assert_overhead_allocation_closure.sql` | Scoped pool_totals + allocation_totals to closed months / is_estimated=FALSE |

No changes to `fact_order_costs.sql` or `fact_order_economics.sql` — both already handled correctly:
- `fact_order_costs.sql` line 197 already had `CASE WHEN a.is_overhead_estimated THEN 'estimated' ELSE 'actual' END AS fee_source`
- `fact_order_economics.sql` already had `BOOL_OR(is_overhead_estimated)` → auto-propagates

---

## Tasks Completed

- [x] `int_order_overhead_allocation`: UNION actual branch (scoped `< current month`) + estimate branch (N=3 trailing, `>= current month`)
- [x] `assert_overhead_allocation_closure`: scoped `pool_totals` to `period_month < DATE_TRUNC('month', CURRENT_DATE)` and `allocation_totals` to `is_overhead_estimated = FALSE`
- [x] `fact_order_costs`: verified no change needed (fee_source logic already present)
- [x] `fact_order_economics`: verified no change needed (BOOL_OR already present)
- [x] `docker compose restart data_platform` — manifest reloaded
- [x] `dbt run` — PASS=3 WARN=0 ERROR=0
- [x] `dbt test` — PASS=21 WARN=0 ERROR=0 (including `assert_overhead_allocation_closure`)
- [x] Verification queries confirmed

---

## dbt Run / Test Summary

```
dbt run:  PASS=3 WARN=0 ERROR=0  (int_order_overhead_allocation, fact_order_costs, fact_order_economics)
dbt test: PASS=21 WARN=0 ERROR=0
  assert_overhead_allocation_closure → PASS
  dbt_utils_unique_combination (order_code+pool_id) → PASS
  not_null_is_overhead_estimated → PASS
  [all 21 tests pass]
```

---

## Verification Numbers

### June 2026 (current unclosed month) — estimate branch

| Pool | Orders | Total (VND) | fee_source |
|---|---|---|---|
| admin (net_revenue) | 23 | 47,967,272 | estimated |
| marketing (net_revenue) | 23 | 4,959,854 | estimated |
| selling (net_revenue) | 23 | 2,830,018 | estimated |
| handling (order_count) | 23 | 197,101 | estimated |
| **TOTAL** | **23** | **55,954,245** | estimated |

- `is_overhead_estimated = TRUE` for all June rows ✓
- 92 allocation rows (23 × 4 pools) ✓
- Avg per fulfilled order: **2.43M VND** (scout estimated ~3.6M; delta explained below)
- `fact_order_costs` June OVERHEAD rows all `fee_source='estimated'` ✓
- `fact_order_economics` June orders: `allocated_overhead IS NOT NULL`, `is_overhead_estimated=TRUE`, `fully_loaded_net_profit` non-null ✓

### Closed months (Jan–May 2026) — actual branch unchanged

- May 2026: `is_overhead_estimated=FALSE`, 138 rows, total 233.6M (admin+marketing+selling) — closure exact ✓
- All months: `is_overhead_estimated=FALSE` confirmed ✓
- `fact_order_costs` May rows: `fee_source='actual'` ✓
- Closure test passes (ABS(diff) ≤ 1 VND for all closed months) ✓

---

## Concern: June estimate ~55.9M vs scout's ~83.4M

**Delta is real and expected — not a bug.** Scout estimate used June NR=214.2M; actual June NR as of 2026-06-05 is lower (month is not finished). The trailing RATES are correct:
- admin: 33.4% × actual-NR-to-date → 47.97M (vs scout's 71.55M using full-month NR)
- marketing: 3.45% → 4.96M; selling: 1.97% → 2.83M; handling: 8,570×23=197K

As more June orders arrive through month-end, the estimate will grow. The formula correctly applies trailing rates to actual-NR-to-date, so the June total will converge toward the scout's ~83M by June 30. This is correct behavior — estimate updates each nightly run.

---

## Implementation Notes

- **ICT month boundary**: uses `DATE_TRUNC('month', CURRENT_DATE)` — DuckDB session `TimeZone=Asia/Ho_Chi_Minh` per `profiles.yml` → ICT-correct, matching existing codebase pattern in `mart_sku_economics_monthly.sql`
- **QUALIFY syntax** (DuckDB): used in `trailing_pool` CTE to get last 3 closed months per pool — correct DuckDB v1 syntax, avoids subquery
- **No new columns**: `is_overhead_estimated` + `allocated_overhead` already existed in both fact tables → no serving layer schema change, no bootstrap needed
- **Model line count**: 213 lines (slightly >200) — all logic in CTEs within single file per OD-1; content warrants the length (two distinct branches with clear separation)
- **Handling pool behavior**: only 2 months in trailing window (Mar+Apr; May has no handling pool) — trailing rate = 2,339,500 / 273 = 8,570 VND/order; correct per scout Q3 note

---

## Unresolved Questions

**Q-concern**: June estimate magnitude (~55.9M) will grow to ~83M by month-end as more orders arrive. Business should expect the nightly number to increase through June 30 — this is correct behavior, not drift.

**Q-scout-Q3 (unresolved)**: May 2026 handling pool absent — business should confirm whether May packaging costs were genuinely zero or not yet booked. Affects trailing rate accuracy for handling pool.

**Q-scout-Q4 (unresolved)**: May 2026 admin spike (198M vs Mar 116M, Apr 107M) likely inflates June admin estimate. After June closes, monitor actual vs estimate gap.

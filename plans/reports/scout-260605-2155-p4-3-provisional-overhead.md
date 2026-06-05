# Scout Report: P4-3 Provisional Overhead Estimate (Q4-B)
**Date:** 2026-06-05 | **Task:** Design Phase-04 P4-3 | **Status:** READ-ONLY

---

## Summary

**YES — there is an unclosed month with orders right now (2026-06).** The June 2026 MISA
account-ledger export has only 3 entries (12 rows total): `64214` (excluded/promo), `642172`
(marketing pool) + `6422` (admin pool, tiny 444K vs typical 107–198M). June is clearly
mid-month-partial, not closed. The 23 fulfilled June orders currently get `is_overhead_estimated=FALSE`
with only ~9.1M total overhead (admin+marketing partial pools), vs ~83M estimated from trailing
3-month rates — they are allocated but drastically under-estimated (~11% of expected). This is the
core P4-3 gap. Trailing 3m rates are: admin 33.4% NR, marketing 3.5% NR, selling 1.97% NR,
handling 8,570 VND/order. Est total June overhead = **83.4M VND** for 23 fulfilled orders.

---

## A. Current Engine Mechanics

### A1. How `int_overhead_pool_monthly` defines "closed month"

No explicit "closed month" flag — a month is implicitly "closed" if it has rows in
`std_misa_account_ledger` (the processed MISA export). The model does:

```sql
-- ledger_classified: INNER JOIN ledger to classification (keep_* treatments only)
FROM std_misa_account_ledger m
INNER JOIN stg_overhead_account_classification c
    ON  m.account = c.account
    AND m.period_month >= c.effective_from
    AND (c.effective_to IS NULL OR m.period_month <= c.effective_to)
-- GROUP BY pool_id, base_metric, period_month
```

**A closed month = any month present in `std_misa_account_ledger` that matches a `keep_*`
classification.** There is no explicit "closed" boolean. A PARTIAL month (like June 2026: only
2 keep_* accounts booked) also produces pool rows — just with incomplete amounts.

Data reality: pools exist for 2026-01 through 2026-06. Pre-2026 = no ledger data = no pool rows.

### A2. How `int_order_overhead_allocation` joins orders to pool

Key lines:
```sql
fulfilled_orders AS (
    SELECT order_code,
           DATE_TRUNC('month', strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS period_month,
           net_revenue
    FROM fact_orders
    WHERE first_shipped_at IS NOT NULL OR status = 'COMPLETED'
),
...
FROM fulfilled_orders o
INNER JOIN int_overhead_pool_monthly p
    ON o.period_month = p.period_month    -- <-- INNER JOIN on period_month
INNER JOIN period_totals pt ON o.period_month = pt.period_month
```

**Grain:** one row per (order_code, pool_id).
**Base columns per pool:** `net_revenue` for admin/marketing/selling; `1.0` (constant) for
order_count (handling).
**Fulfilled filter:** `first_shipped_at IS NOT NULL OR status='COMPLETED'`.
**INNER JOIN behavior:** orders whose period_month has NO pool row → no allocation row → NULL
`allocated_overhead` in fact_order_economics (confirmed for all 2021–2025 orders; 2,737 orders with
NULL overhead).

**What happens to June 2026 orders:** they DO get allocation rows (from the partial June pool),
so `allocated_overhead IS NOT NULL` and `is_overhead_estimated = FALSE`. But the amount is ~9.1M
vs ~83M expected. **This is wrong/misleading, not NULL.** P4-3 must handle this.

### A3. Closure test exact logic

`transformation/tests/assert_overhead_allocation_closure.sql`:
```sql
-- LEFT JOIN int_overhead_pool_monthly → int_order_overhead_allocation
-- Asserts: ABS(pool_net - SUM(allocated_amount)) <= 1 VND per (pool_id, period_month)
-- Returns offending rows — test FAILS if any rows returned
```

**Grain of assertion:** per `(pool_id, period_month)` across ALL pool rows in
`int_overhead_pool_monthly`. Closure is mathematically guaranteed by the pro-rata formula for
closed months. **Problem for P4-3:** if we add estimated pool rows (provisional), the closure
test will include them. Since estimated pools are synthetic (not from MISA actual), they must be
excluded from the closure assertion.

### A4. `overhead_allocation_config` / `budgeted_rate` existence

**`overhead_allocation_config` does NOT exist as a table or seed.** The design doc references it
as a gsheet source (like marketing_spend), but it has NOT been implemented. The ingestion script
`gsheet_overhead_classification.py` ingests the classification table (treatment/pool/base) only —
no `budgeted_rate` column.

The `stg_overhead_account_classification` raw parquet has columns:
`account, account_group, treatment, pool_id, base_metric, channel, effective_from, effective_to,
note, ingest_method`. **No `budgeted_rate` column anywhere.**

The design doc (Q4-B, line 304) says: `overhead_allocation_config.budgeted_rate` "already exists"
— but **this is aspirational design, not implemented reality.** No such config table/column exists.
P4-3 trailing-rate approach is therefore the ONLY available fallback (and it's better than a
manually-maintained budgeted_rate anyway).

---

## B. Data Reality

### B1. Actual pool months in `int_overhead_pool_monthly`

| period_month | admin | handling | marketing | selling |
|---|---|---|---|---|
| 2026-01 | 107,489,927 | — | 16,637,019 | 9,194,065 |
| 2026-02 | 112,036,623 | — | 16,344,229 | 3,548,169 |
| 2026-03 | 116,108,474 | 1,050,000 | 11,343,410 | 3,146,451 |
| 2026-04 | 107,205,460 | 1,289,500 | 15,692,816 | 3,260,938 |
| 2026-05 | 198,528,806 | — | 16,582,645 | 18,480,888 |
| **2026-06** | **444,946** | **—** | **8,658,024** | **—** |

**Latest "fully closed" month = 2026-05** (3 accounts contributing admin, typical amounts). 2026-06
is clearly PARTIAL (admin=444K vs 107-198M typical; only 2 pools; no selling, no handling).

### B2. June 2026 unclosed month — order counts

| | Count |
|---|---|
| Total June orders | 45 |
| Fulfilled June orders (would get overhead) | **23** |
| Current allocation rows for June | 23 orders × 2 pools = 46 rows |
| Current allocated_overhead for June (partial actual) | ~9.1M VND |
| is_overhead_estimated for June | FALSE (misleadingly) |

Historical (2021-2025): 2,737 orders have `allocated_overhead IS NULL` (no MISA ledger for those years).

### B3. Current `is_overhead_estimated` — all FALSE everywhere

```
is_overhead_estimated=FALSE: 2,236 allocation rows (all of them)
```

No estimated rows exist yet. The design placeholder `is_overhead_estimated=FALSE` is the
hardcoded literal in the current SQL (comment says "provisional/trailing-rate is a future phase").

### B4. Sample trailing rate per pool (last 3 closed months: Mar–May 2026)

| Pool | Base | Sum pool (3m) | Sum base (3m) | Trailing rate |
|---|---|---|---|---|
| admin | net_revenue | 421,842,740 | 1,262,987,525 | **33.40% of NR** |
| marketing | net_revenue | 43,618,871 | 1,262,987,525 | **3.45% of NR** |
| selling | net_revenue | 24,888,277 | 1,262,987,525 | **1.97% of NR** |
| handling | order_count | 2,339,500 | 273 orders | **8,570 VND/order** |

Note: admin rate varies 21–67% across months (high variance due to May spike in 6422 base).
This is the main reason to use 3-month trailing vs 1-month.

**Estimated June 2026 overhead from trailing rates:**
- admin: 33.40% × 214,219,819 (Jun NR) = **71,550,252 VND**
- marketing: 3.45% × 214,219,819 = **7,398,352 VND**
- selling: 1.97% × 214,219,819 = **4,221,389 VND**
- handling: 8,570 × 23 orders = **197,101 VND**
- **Total estimate: ~83.4M VND** for 23 orders → avg 3.6M/order

This is the order-of-magnitude check; actual closed June numbers will differ.

---

## C. Implementation Design (9 Points)

### C1. Where estimate logic lives — RECOMMENDATION: extend `int_order_overhead_allocation` with UNION branch

**Option A: extend existing model** — add a second branch via UNION ALL in
`int_order_overhead_allocation`: one branch for actual/closed periods, one for estimated/unclosed.

**Option B: new intermediate model `int_overhead_provisional_rate`** that computes the trailing
rate, then `int_order_overhead_allocation` does UNION ALL with it.

**Recommend Option B** (KISS + separation of concerns):
- `int_order_overhead_allocation` stays clean (actual allocation logic only, line count stays low).
- New `int_overhead_provisional_rate` (small model ~60 lines): computes trailing N-month rate per
  pool, applies to unclosed-month fulfilled orders → emits estimated allocation rows.
- `int_order_overhead_allocation` is then a UNION ALL of actual rows + provisional rows.
  Wait — actually the UNION in the parent creates a circular dependency if the parent reads itself.
  
**Better: create `int_overhead_provisional_allocation` as a SIBLING model** that:
  1. Reads `int_overhead_pool_monthly` to compute trailing rates (last N closed months).
  2. Reads `fact_orders` (same fulfilled filter) for unclosed months only.
  3. Emits estimated allocation rows with `is_overhead_estimated = TRUE`.

Then `fact_order_economics` and `fact_order_costs` JOIN/UNION **both** models: 
`int_order_overhead_allocation` (actual) + `int_overhead_provisional_allocation` (estimated).

**Alternative KISS**: extend `int_order_overhead_allocation` itself with a UNION ALL at the end
that appends estimated rows. This keeps one model as the single source of truth, avoids
downstream model changes. **Preferred if model stays < 200 lines.**

**OPEN DECISION OD-1:** single model with UNION branch vs sibling model. Recommend single model
for KISS — adds ~60 lines, stays under 200. Orchestrator to confirm.

### C2. Trailing window N — RECOMMEND N=3, mark as OPEN DECISION

- N=1: easiest SQL, but high variance (admin rate varied 21-67% across months).
- N=3: smoother, captures seasonal variation, data shows 3 closed months available.
- N=6: more stable but may miss recent cost structure changes.

**Recommend N=3 (last 3 closed months).** Rationale: admin pool has high month-to-month variance
(May 2026 admin was 198M vs Apr 107M, likely year-end adjustments); 3-month smooths this without
being too stale. Also 3 months is the minimum where handling pool has data (only Mar+Apr have
handling; May-June don't — see below).

**OPEN DECISION OD-2 for orchestrator:** confirm N=3 or override.

**SPECIAL CASE for handling:** handling pool only appears in 2 of 5 closed months (Mar, Apr).
May and June have no handling data. Trailing rate uses only months where that pool_id exists.
If handling has zero months in trailing window → fallback to 0 (no handling estimate). This is
correct behavior (if handling wasn't booked, assume zero for current month).

### C3. Unclosed-month detection — RECOMMEND current-calendar-month approach

**Simplest and most correct:** unclosed months = `period_month >= DATE_TRUNC('month', CURRENT_DATE)`.

This correctly identifies June 2026 today. No need to compare pool completeness or count accounts.
When MISA closes June and the export arrives (next month), `period_month < DATE_TRUNC('month', CURRENT_DATE)` → June moves to closed, estimate naturally disappears.

**Alternative: anti-join approach** — months with fulfilled orders but no pool_net from actual
MISA. This catches historical nulls (2021-2025) which we do NOT want to estimate (too far back,
no trailing rate context). The calendar-month approach is safer.

**SQL:**
```sql
-- Unclosed months = current calendar month (not yet MISA-closed)
WHERE period_month = DATE_TRUNC('month', CURRENT_DATE)
-- AND pool exists in int_overhead_pool_monthly (partial or not)
-- The partial pool is REPLACED by the estimate — see C4 for overwrite approach
```

**CRITICAL NUANCE (discovered):** June 2026 currently HAS pool rows (partial: admin=444K,
marketing=8.6M) AND those orders are already allocated via INNER JOIN. The estimate must REPLACE
(not supplement) these partial actual rows. This means the UNION branch approach must exclude
unclosed months from the actual-branch and include them only in the estimated-branch.

```sql
-- Actual branch: fulfilled orders for CLOSED months only
WHERE o.period_month < DATE_TRUNC('month', CURRENT_DATE)

-- Estimated branch: fulfilled orders for CURRENT (unclosed) month only
WHERE o.period_month = DATE_TRUNC('month', CURRENT_DATE)
```

### C4. Per-pool trailing rate SQL (sketch)

```sql
-- Step 1: trailing rate per pool (last N closed months with pool data)
trailing_rates AS (
    SELECT
        pool_id,
        base_metric,
        -- Only closed months (not current calendar month)
        SUM(pool_net) AS sum_pool,
        ROW_NUMBER() OVER (PARTITION BY pool_id ORDER BY period_month DESC) AS rn
    FROM int_overhead_pool_monthly
    WHERE period_month < DATE_TRUNC('month', CURRENT_DATE)
    QUALIFY rn <= 3  -- last 3 closed months per pool
),
pooled_rates AS (
    SELECT pool_id, base_metric, SUM(sum_pool) AS tot_pool
    FROM trailing_rates GROUP BY pool_id, base_metric
),
-- Must also compute sum of base (net_revenue, order_count) over same window
-- This requires joining back to fact_orders for those closed months
trailing_base AS (
    SELECT
        DATE_TRUNC('month', strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS period_month,
        SUM(net_revenue) AS tot_net_revenue,
        COUNT(*) AS tot_order_count
    FROM fact_orders
    WHERE (first_shipped_at IS NOT NULL OR status = 'COMPLETED')
      AND period_month IN (SELECT DISTINCT period_month FROM trailing_months)
    GROUP BY 1
),
-- rate = SUM(pool over N months) / SUM(base over N months)
rates AS (
    SELECT
        pr.pool_id,
        pr.base_metric,
        pr.tot_pool / NULLIF(SUM(CASE pr.base_metric
            WHEN 'net_revenue' THEN tb.tot_net_revenue
            WHEN 'order_count' THEN tb.tot_order_count END), 0) AS trailing_rate
    FROM pooled_rates pr
    JOIN trailing_base tb ON ... -- aggregated over window months
)

-- Step 2: apply rate to current-month fulfilled orders
provisional AS (
    SELECT
        o.order_code,
        r.pool_id,
        o.period_month,
        r.base_metric,
        r.trailing_rate * CASE r.base_metric
            WHEN 'net_revenue' THEN o.net_revenue
            WHEN 'order_count' THEN 1.0
        END AS allocated_amount,
        TRUE AS is_overhead_estimated
    FROM current_month_fulfilled_orders o
    CROSS JOIN rates r
)
```

Note: CROSS JOIN rates is correct — each order gets one row per pool (same pattern as actual).
No closure test on provisional rows (by design).

### C5. `is_estimated` flag propagation

- `int_order_overhead_allocation` (actual branch): `FALSE` (hardcoded, as today).
- New provisional branch: `TRUE` (hardcoded).
- `fact_order_economics.is_overhead_estimated`: already `BOOL_OR(is_overhead_estimated)` from
  the JOIN to `int_order_overhead_allocation` (or both models if split). **No change needed
  to fact_order_economics SQL** — the BOOL_OR automatically picks up TRUE from estimated rows.

### C6. Closure test fix — scope to `is_estimated = FALSE`

Current closure test LEFT JOINs `int_overhead_pool_monthly` → `int_order_overhead_allocation`.
With P4-3:
1. Actual branch produces closure for closed months (mathematical guarantee holds).
2. Estimated branch for current month produces NO actual pool rows to compare against.
3. June 2026 partial pool rows (admin=444K, marketing=8.6M) must also be excluded from closure
   since they'll no longer be in the actual branch.

**Fix: filter closure test to closed months only:**
```sql
-- In assert_overhead_allocation_closure.sql, add:
WHERE p.period_month < DATE_TRUNC('month', CURRENT_DATE)
-- This excludes the current (unclosed) month from closure assertion
```

Also filter `allocation_totals` CTE to `is_overhead_estimated = FALSE` rows only:
```sql
WHERE is_overhead_estimated = FALSE
```

Both filters are needed. The test remains meaningful for all closed/actual months.

### C7. OVERHEAD cost rows in `fact_order_costs` — RECOMMEND include estimated with `fee_source='estimated'`

Currently: OVERHEAD rows use `fee_source='actual'` and `source_system='derived'`.

**Recommended for P4-3 estimated rows:**
- `fee_source = 'estimated'` (distinguishes from closed-actual `fee_source='allocated'`)
  - Note: current actual OVERHEAD rows use `fee_source='actual'` — check `fact_order_costs.sql`
    to confirm the exact value used.
- `source_system = 'derived'` (same, since derived from trailing calculation)
- `cost_category = 'OVERHEAD'`, `cost_type = 'overhead_admin'` / etc (same pattern)

This is important for dashboards to filter/flag estimated overhead costs.

**OPEN DECISION OD-3:** does the orchestrator/business want estimated OVERHEAD rows in
`fact_order_costs`, or only in `fact_order_economics`? Recommend YES (include) for full
long-format coverage; dashboards can filter by `fee_source`.

### C8. Idempotent overwrite when actual arrives

The pipeline is **full-rebuild / rolling parquet** (not incremental appends). When June MISA
ledger is fully exported and ingested:
- `std_misa_account_ledger` gains all June accounts → `int_overhead_pool_monthly` gets full
  June pool → `int_order_overhead_allocation` actual branch now covers June → estimated branch
  for June becomes empty (period_month < DATE_TRUNC('month', CURRENT_DATE) once July starts).
- Models are re-materialized from scratch on each nightly run.
- Result: estimate automatically replaced by actual on July 1 nightly run. **No special
  restate logic needed. Confirmed.**

**One edge case:** if MISA export for June arrives mid-June (before month closes), the estimate
branch still applies (period_month = current month). The partial pool is excluded from actual
branch. Correct behavior — trust trailing rate > partial actual during unclosed month.

### C9. New dbt node — restart + bootstrap needed?

Yes to both:
- **Adding `int_overhead_provisional_allocation` (new model)** or extending
  `int_order_overhead_allocation` with new columns: either way, `data_platform` container must
  be restarted (manifest is pre-parsed at startup, not hot-reloaded — per MEMORY note).
- **`is_overhead_estimated` column already exists** in `fact_order_economics` and
  `fact_order_costs` (OVERHEAD rows) — no new columns needed there.
- **Serving views:** DuckDB serving bootstrap (`bootstrap_serving_views.py`) needed if the
  mart parquet files change schema. Since `fact_order_economics` gains no new columns (only
  data changes), bootstrap may not be strictly required — but should be run after dbt for safety
  (stop Metabase first per MEMORY note).
- **If extending `int_order_overhead_allocation`:** no new model = no manifest issue; restart
  still recommended as best practice after SQL changes.

---

## D. Verify Protocol (for implementer + orchestrator)

1. `docker exec data_platform dbt run --select int_overhead_pool_monthly int_order_overhead_allocation fact_order_economics fact_order_costs` — must succeed.
2. `docker exec data_platform dbt test --select assert_overhead_allocation_closure` — must pass (scoped to closed months).
3. Query: `SELECT period_month, is_overhead_estimated, COUNT(*), SUM(allocated_amount) FROM int_order_overhead_allocation GROUP BY 1,2 ORDER BY 1` — June 2026 rows must show `is_overhead_estimated=TRUE`, amount ~83M; May and earlier must be `FALSE`.
4. Spot-check: `fact_order_economics` for a June order: `allocated_overhead IS NOT NULL`, `is_overhead_estimated=TRUE`, `fully_loaded_net_profit` not NULL.
5. Spot-check: closed months unchanged (is_overhead_estimated=FALSE, closure assertion < 1 VND diff).
6. Dagster materialize `transform_batch_nightly_job` — zero errors.
7. Confirm `channel_net_profit` byte-identical before/after (overhead does not touch tier-2).

---

## Risks / Unresolved Questions

**OD-1 (OPEN DECISION):** Single model UNION branch vs sibling model for provisional allocation.
Recommend single model (KISS). Orchestrator confirm.

**OD-2 (OPEN DECISION):** Trailing window N. Recommend N=3. Orchestrator confirm (or business
can specify N based on seasonality awareness).

**OD-3 (OPEN DECISION):** Include estimated OVERHEAD rows in `fact_order_costs`. Recommend YES.

**Q1 — Partial-pool handling:** Current design proposes replacing partial June pool (actual
admin=444K, marketing=8.6M) with trailing estimates. This means the existing June MISA data is
IGNORED during the unclosed period. This is correct (partial data is misleading), but
orchestrator should confirm this is acceptable — i.e., it's OK to discard those 2 MISA entries
until month closes.

**Q2 — `overhead_allocation_config` non-existent:** The design doc references this as existing
and containing `budgeted_rate`. It does NOT exist. P4-3 must use trailing-rate approach exclusively
(no `budgeted_rate` fallback available). If first-month bootstrap is needed (no trailing history),
either (a) use hardcoded rate from orchestrator, or (b) emit NULL for periods with no trailing
history. Since data starts 2026-01 and today is 2026-06, there are 5 closed months → trailing
rate always available from January onward.

**Q3 — May 2026 handling pool absent:** May has no handling pool row (only Mar+Apr have handling).
Trailing 3m window for handling = only 2 months. June estimate for handling = 8,570 VND/order
based on 2-month average. If May genuinely had no packaging costs, the trailing rate for June
should be lower. **Business should confirm if May handling was zero or simply not booked yet.**

**Q4 — High admin rate variance (21-67%):** May 2026 admin = 198M vs Mar 116M, Apr 107M.
This is a large spike. If May's spike was a one-time catch-up, trailing rate will over-estimate
June. Monitor after June closes. Recommend N=3 smooths this; N=1 (May only) would be worst-case.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Full engine mechanics documented, data reality verified, implementation design specified (9 points). June 2026 is the unclosed month with 23 fulfilled orders, currently allocated ~9.1M (partial actual, misleadingly flagged FALSE) vs est ~83M from trailing 3-month rates.
**Concerns/Blockers:** (1) `overhead_allocation_config.budgeted_rate` does not exist — trailing rate is the only approach. (2) Partial pool replacement (discarding partial June MISA entries) needs orchestrator confirmation. (3) Three open decisions (OD-1/OD-2/OD-3) need orchestrator input before implementation.

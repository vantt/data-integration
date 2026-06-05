-- =================================================================================================
-- SINGULAR TEST: OVERHEAD ALLOCATION CLOSURE
-- =================================================================================================
-- Invariant: for every (pool_id, period_month) in CLOSED months, the sum of allocated_amount
-- across all fulfilled orders MUST equal the pool's pool_net.
--
-- CLOSED month = period_month < DATE_TRUNC('month', CURRENT_DATE).
-- The current (unclosed) month uses a trailing-rate estimate (is_overhead_estimated=TRUE)
-- and is deliberately excluded — estimated rows have no MISA pool to close against.
--
-- This is the closure guarantee — the allocation is a pure pro-rata redistribution:
--   Σ (pool_net × order_base / tot_base)  =  pool_net × (Σ order_base / tot_base)
--                                          =  pool_net × (tot_base / tot_base)
--                                          =  pool_net   (when tot_base ≠ 0)
--
-- Rounding tolerance: ABS(diff) > 1 (i.e. ≤ 1 VND rounding error is acceptable given
-- that pool_net is BIGINT and allocated_amount uses floating-point division).
--
-- Returns offending (pool_id, period_month) rows — test FAILS if any rows are returned.
-- =================================================================================================

WITH pool_totals AS (
    SELECT
        pool_id,
        period_month,
        pool_net
    FROM {{ ref('int_overhead_pool_monthly') }}
    -- Scope to closed months only (current month has partial MISA data; estimate not closure-checked)
    WHERE period_month < DATE_TRUNC('month', CURRENT_DATE)
),

allocation_totals AS (
    SELECT
        pool_id,
        period_month,
        SUM(allocated_amount) AS sum_allocated
    FROM {{ ref('int_order_overhead_allocation') }}
    -- Only actual (non-estimated) rows participate in the closure assertion
    WHERE is_overhead_estimated = FALSE
    GROUP BY pool_id, period_month
),

closure_check AS (
    SELECT
        p.pool_id,
        p.period_month,
        p.pool_net,
        a.sum_allocated,
        p.pool_net - COALESCE(a.sum_allocated, 0) AS diff
    FROM pool_totals p
    -- LEFT JOIN to surface pools with no allocated rows (sum_allocated = NULL → diff = pool_net)
    LEFT JOIN allocation_totals a
        ON  p.pool_id      = a.pool_id
        AND p.period_month = a.period_month
)

SELECT
    pool_id,
    period_month,
    pool_net,
    sum_allocated,
    diff
FROM closure_check
-- Allow ≤ 1 VND floating-point rounding error; flag anything larger as a real closure break
WHERE ABS(diff) > 1

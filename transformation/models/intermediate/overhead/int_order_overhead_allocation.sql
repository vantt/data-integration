{{ config(
    tags=['int', 'overhead'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INT: ORDER OVERHEAD ALLOCATION
-- =================================================================================================
-- Grain:   (order_code, pool_id) — one row per fulfilled order × overhead pool
-- Purpose: Spread each month's overhead pool_net down to individual orders pro-rata
--          by the pool's base_metric (net_revenue | order_count).
--
-- Source = fact_orders (NOT fact_order_economics) — IMPORTANT: fact_order_economics consumes
--   this allocation (allocated_overhead → fully_loaded_net_profit), so reading it here would
--   create a dependency cycle. The base metrics needed (net_revenue, order_count) are all in
--   fact_orders. (gross_profit base is not used by any pool today; supporting it would need COGS
--   from int_order_cogs_reconciled — deferred until a pool actually requires it.)
--
-- Fulfilled-order rule (§Q5):
--   fulfilled = first_shipped_at IS NOT NULL OR status = 'COMPLETED'.
--
-- Two branches (P4-3 — OD-4):
--   ACTUAL:    period_month < current calendar month (ICT) → pro-rata from MISA actual pool.
--              Closure invariant holds. is_overhead_estimated = FALSE.
--   ESTIMATED: period_month >= current calendar month (ICT) → trailing N=3 closed-month rate.
--              Partial current-month MISA pool is DISCARDED (replaced by trailing estimate).
--              is_overhead_estimated = TRUE.
--
-- Current date uses CURRENT_DATE (DuckDB session TimeZone=Asia/Ho_Chi_Minh per profiles.yml),
-- so DATE_TRUNC('month', CURRENT_DATE) is ICT-correct for month boundaries.
-- =================================================================================================

WITH orders AS (
    SELECT
        order_code,
        date_key,            -- INTEGER YYYYMMDD
        status,
        first_shipped_at,
        net_revenue
    FROM {{ ref('fact_orders') }}
),

-- Step 1: ALL fulfilled orders + period_month derived from date_key
fulfilled_orders AS (
    SELECT
        order_code,
        -- date_key is INTEGER YYYYMMDD; strptime parses it to DATE
        DATE_TRUNC('month', strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS period_month,
        net_revenue
    FROM orders
    WHERE first_shipped_at IS NOT NULL
       OR status = 'COMPLETED'
),

-- ==========================================================================
-- BRANCH A: ACTUAL (closed months only — period_month < current ICT month)
-- ==========================================================================

-- Step A1: fulfilled orders for closed months only
actual_orders AS (
    SELECT order_code, period_month, net_revenue
    FROM fulfilled_orders
    WHERE period_month < DATE_TRUNC('month', CURRENT_DATE)
),

-- Step A2: period base totals for actual months
actual_period_totals AS (
    SELECT
        period_month,
        SUM(net_revenue) AS tot_net_revenue,
        COUNT(*)         AS tot_order_count
    FROM actual_orders
    GROUP BY period_month
),

-- Step A3: actual allocation per (order, pool)
actual_allocated AS (
    SELECT
        o.order_code,
        p.pool_id,
        o.period_month,
        p.base_metric,
        CASE p.base_metric
            WHEN 'net_revenue' THEN o.net_revenue
            WHEN 'order_count' THEN 1.0
        END AS order_base,
        CASE p.base_metric
            WHEN 'net_revenue' THEN pt.tot_net_revenue
            WHEN 'order_count' THEN pt.tot_order_count
        END AS tot_base,
        p.pool_net
    FROM actual_orders o
    INNER JOIN {{ ref('int_overhead_pool_monthly') }} p
        ON o.period_month = p.period_month
    INNER JOIN actual_period_totals pt
        ON o.period_month = pt.period_month
),

-- ==========================================================================
-- BRANCH B: ESTIMATED (current month onward — trailing N=3 rate, OD-2)
-- ==========================================================================

-- Step B1: trailing 3 closed months per pool (only months with pool data)
-- QUALIFY applies ROW_NUMBER after the pool filter → gets up to 3 most recent per pool_id
trailing_pool AS (
    SELECT
        pool_id,
        base_metric,
        period_month,
        pool_net,
        ROW_NUMBER() OVER (PARTITION BY pool_id ORDER BY period_month DESC) AS rn
    FROM {{ ref('int_overhead_pool_monthly') }}
    WHERE period_month < DATE_TRUNC('month', CURRENT_DATE)
    QUALIFY rn <= 3
),

-- Step B2: aggregate pool totals over the trailing window per pool
trailing_pool_totals AS (
    SELECT
        pool_id,
        base_metric,
        SUM(pool_net) AS sum_pool
    FROM trailing_pool
    GROUP BY pool_id, base_metric
),

-- Step B3: aggregate fulfilled-order base over the same trailing months per pool
-- (only months that appear in the trailing window for that pool)
trailing_base AS (
    SELECT
        tp.pool_id,
        tp.base_metric,
        SUM(CASE tp.base_metric
            WHEN 'net_revenue' THEN fo.net_revenue
            WHEN 'order_count' THEN 1.0
        END) AS sum_base
    FROM trailing_pool tp
    JOIN fulfilled_orders fo
        ON fo.period_month = tp.period_month
    GROUP BY tp.pool_id, tp.base_metric
),

-- Step B4: trailing rate = sum_pool / sum_base (VND per NR unit, or VND per order)
trailing_rates AS (
    SELECT
        pt.pool_id,
        pt.base_metric,
        pt.sum_pool / NULLIF(tb.sum_base, 0) AS trailing_rate
    FROM trailing_pool_totals pt
    JOIN trailing_base tb
        ON pt.pool_id    = tb.pool_id
       AND pt.base_metric = tb.base_metric
    -- Exclude pools where trailing rate cannot be computed (no base data in window)
    WHERE pt.sum_pool IS NOT NULL
      AND tb.sum_base  IS NOT NULL
      AND tb.sum_base  > 0
),

-- Step B5: current-month fulfilled orders (apply estimate to these)
current_orders AS (
    SELECT order_code, period_month, net_revenue
    FROM fulfilled_orders
    WHERE period_month >= DATE_TRUNC('month', CURRENT_DATE)
),

-- Step B6: estimated allocation — CROSS JOIN each current-month order with each pool rate
estimated_allocated AS (
    SELECT
        o.order_code,
        r.pool_id,
        o.period_month,
        r.base_metric,
        CASE r.base_metric
            WHEN 'net_revenue' THEN o.net_revenue
            WHEN 'order_count' THEN 1.0
        END AS order_base,
        r.trailing_rate,
        CASE r.base_metric
            WHEN 'net_revenue' THEN r.trailing_rate * o.net_revenue
            WHEN 'order_count' THEN r.trailing_rate * 1.0
        END AS allocated_amount
    FROM current_orders o
    CROSS JOIN trailing_rates r
    -- Only emit rows when a trailing rate exists; if zero pools have history → no rows (OD-2 fallback)
    WHERE r.trailing_rate IS NOT NULL
)

-- ==========================================================================
-- FINAL OUTPUT: UNION actual + estimated
-- ==========================================================================

-- ACTUAL branch
SELECT
    order_code,
    pool_id,
    period_month,
    base_metric,
    pool_net * order_base / NULLIF(tot_base, 0)     AS allocated_amount,
    FALSE                                           AS is_overhead_estimated
FROM actual_allocated

UNION ALL

-- ESTIMATED branch (trailing rate × per-order base)
SELECT
    order_code,
    pool_id,
    period_month,
    base_metric,
    CAST(allocated_amount AS DOUBLE)                AS allocated_amount,
    TRUE                                            AS is_overhead_estimated
FROM estimated_allocated

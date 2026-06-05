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
--     - first_shipped_at NOT NULL → the order was shipped = consumed fulfillment ops
--       (incl. RTO / cancelled-after-ship → correctly stays in scope per Q5).
--     - status = 'COMPLETED' → belt-and-suspenders for completed orders.
--   Excludes cancelled-pre-ship + DRAFT (never left the warehouse → absorb no overhead).
--
-- Allocation formula (per fulfilled order o, per pool p in the same period_month):
--   order_base       = the order's share of the pool base (net_revenue, or 1 for order_count)
--   tot_base         = sum of order_base across ALL fulfilled orders in the same period_month
--   allocated_amount = pool_net × (order_base / tot_base)
--   Closure: Σ allocated_amount per period == Σ pool_net per period (assert_overhead_allocation_closure).
--
-- Edge cases:
--   - order_base = 0 (net_revenue=0 for a net_revenue pool) → allocated_amount = 0. Fine.
--   - tot_base = 0 (whole month has 0 net_revenue) → NULLIF guard returns NULL (not expected).
--   - is_overhead_estimated = FALSE: all current data is closed/actual MISA periods.
--     Provisional/trailing-rate estimation is a future phase.
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

-- Step 1: fulfilled orders + period_month derived from date_key
fulfilled_orders AS (
    SELECT
        order_code,
        -- date_key is INTEGER YYYYMMDD; strptime parses it to DATE (plain CAST needs YYYY-MM-DD)
        DATE_TRUNC('month', strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS period_month,
        net_revenue
    FROM orders
    WHERE first_shipped_at IS NOT NULL
       OR status = 'COMPLETED'
),

-- Step 2: period base totals (over fulfilled orders only) — allocation denominators
period_totals AS (
    SELECT
        period_month,
        SUM(net_revenue)    AS tot_net_revenue,
        COUNT(*)            AS tot_order_count
    FROM fulfilled_orders
    GROUP BY period_month
),

-- Step 3: fulfilled orders × pools active in the same period_month
allocated AS (
    SELECT
        o.order_code,
        p.pool_id,
        o.period_month,
        p.base_metric,

        -- Order's share of the base metric for this pool
        CASE p.base_metric
            WHEN 'net_revenue'  THEN o.net_revenue
            WHEN 'order_count'  THEN 1.0
        END AS order_base,   -- gross_profit base not supported v1 (no pool uses it)

        -- Period total for the same base metric (denominator)
        CASE p.base_metric
            WHEN 'net_revenue'  THEN pt.tot_net_revenue
            WHEN 'order_count'  THEN pt.tot_order_count
        END AS tot_base,

        p.pool_net

    FROM fulfilled_orders o
    INNER JOIN {{ ref('int_overhead_pool_monthly') }} p
        ON o.period_month = p.period_month
    INNER JOIN period_totals pt
        ON o.period_month = pt.period_month
)

SELECT
    order_code,
    pool_id,
    period_month,
    base_metric,

    -- Pro-rata allocation: NULLIF guards divide-by-zero when tot_base = 0
    pool_net * order_base / NULLIF(tot_base, 0)     AS allocated_amount,

    -- FALSE = actual closed-period data. Provisional/trailing-rate is a future phase.
    FALSE                                           AS is_overhead_estimated

FROM allocated

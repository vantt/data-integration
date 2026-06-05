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
--          by the pool's base_metric (net_revenue | order_count | gross_profit).
--
-- Fulfilled-order rule (§Q5):
--   An order is "fulfilled" when has_cogs IS TRUE OR net_revenue > 0.
--   Rationale:
--     - has_cogs=TRUE  → MISA has posted a COGS line, proving goods were dispatched
--     - net_revenue>0  → customer was charged (covers cash/prepaid orders where MISA
--                        lags but Sapo revenue is confirmed)
--     - Excludes pure-cancellation orders (status='cancelled', has_cogs=FALSE,
--       net_revenue=0) which never left the warehouse and should not absorb overhead.
--   Note: returned orders that had goods dispatched retain has_cogs=TRUE and remain
--   in scope — their return P&L is tracked separately in fact_order_returns.
--
-- Allocation formula (per fulfilled order o, per pool p in the same period_month):
--   order_base  = the order's share of the pool base (revenue, 1, or gross_profit)
--   tot_base    = sum of order_base across ALL fulfilled orders in the same period_month
--   allocated_amount = pool_net × (order_base / tot_base)
--
-- Edge cases:
--   - gross_profit can be negative → allocated_amount can be negative for that order × pool.
--     This is acceptable: the pool still closes (Σ allocated = pool_net per period).
--   - order_base = 0 (e.g. net_revenue=0 for a net_revenue pool) → allocated_amount = 0. Fine.
--   - tot_base = 0 (entire month has 0 net_revenue) → NULLIF guard returns NULL. Acceptable —
--     it means no orders qualify for that base metric in that month (edge case, not expected).
--   - is_overhead_estimated = FALSE: all current data is from closed/actual MISA periods.
--     Provisional/trailing-rate estimation is a future phase.
-- =================================================================================================

WITH fact_orders AS (
    -- Pull only the columns needed; date_key is INTEGER (YYYYMMDD) in fact_order_economics
    SELECT
        order_code,
        date_key,
        status,
        has_cogs,
        net_revenue,
        gross_profit
    FROM {{ ref('fact_order_economics') }}
),

-- Step 1: fulfilled orders with their base metrics + period_month derived from date_key
fulfilled_orders AS (
    SELECT
        order_code,
        -- date_key is INTEGER YYYYMMDD; strptime parses it to DATE (plain CAST needs YYYY-MM-DD)
        DATE_TRUNC('month', strptime(CAST(date_key AS VARCHAR), '%Y%m%d')::DATE) AS period_month,
        net_revenue,
        gross_profit
    FROM fact_orders
    WHERE
        -- Fulfilled = goods were dispatched and/or customer was charged
        -- See header comment for rationale
        has_cogs IS TRUE
        OR net_revenue > 0
),

-- Step 2: period base totals (over fulfilled orders only)
-- Used as the allocation denominator for each pool's base_metric
period_totals AS (
    SELECT
        period_month,
        SUM(net_revenue)    AS tot_net_revenue,
        COUNT(*)            AS tot_order_count,
        SUM(gross_profit)   AS tot_gross_profit
    FROM fulfilled_orders
    GROUP BY period_month
),

-- Step 3: cross-join fulfilled orders × pools active in the same period_month
-- Each fulfilled order receives one allocation row per active pool
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
            WHEN 'gross_profit' THEN o.gross_profit
        END AS order_base,

        -- Period total for the same base metric (denominator)
        CASE p.base_metric
            WHEN 'net_revenue'  THEN pt.tot_net_revenue
            WHEN 'order_count'  THEN pt.tot_order_count
            WHEN 'gross_profit' THEN pt.tot_gross_profit
        END AS tot_base,

        p.pool_net

    FROM fulfilled_orders o
    -- Join pool rows that are active in this order's period_month
    INNER JOIN {{ ref('int_overhead_pool_monthly') }} p
        ON o.period_month = p.period_month
    -- Attach period totals for denominator computation
    INNER JOIN period_totals pt
        ON o.period_month = pt.period_month
)

SELECT
    order_code,
    pool_id,
    period_month,
    base_metric,

    -- Pro-rata allocation: NULLIF guards against divide-by-zero when tot_base = 0
    -- (entire month with 0 net_revenue / 0 gross_profit — not expected in practice)
    pool_net * order_base / NULLIF(tot_base, 0)     AS allocated_amount,

    -- FALSE = actual closed-period data from MISA.
    -- Provisional/trailing-rate estimation is deferred to a future phase.
    FALSE                                           AS is_overhead_estimated

FROM allocated

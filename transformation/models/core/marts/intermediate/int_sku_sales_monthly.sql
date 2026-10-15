{{ config(
    materialized='table',
    tags=['mart', 'intermediate']
) }}

-- =============================================================================
-- SKU sales monthly (core): sales, velocity, returns and channel concentration per SKU-month
-- =============================================================================
-- Grain: one row per (product_key, snapshot_month), a SKU-month with at least one valid sale.
-- Window: rolling 24 completed months (current open month excluded).
-- Status filter: excludes CANCELLED orders, non-sales channels, the Unknown product and
-- zero-revenue lines (gifts/promos).
--
-- This is the revenue half of the former mart_sku_economics_monthly. Core keeps revenue; the
-- finance pack keeps cost and margin: packs/finance mart_sku_economics_monthly reads every
-- column below from this model unchanged and adds COGS/margin (docs/architecture/modules.md §7).
-- Core readers: int_product_velocity_trend, mart_inventory_health, mart_product_action_queue,
-- mart_product_health.
--
-- Caveats (same as the former mart):
-- 1. return_count / return_rate come from int_return_sku_lines, which attributes a return to
--    every SKU of the originating order proportionally by line revenue: may overstate return
--    exposure for minor SKUs.
-- 2. is_slow_mover is a sales-velocity proxy (no stock data): no sale in the last 14 days of the
--    month AND below the month's top-200 revenue threshold.
-- 3. Only the single top channel by revenue is surfaced.
-- =============================================================================

-- product_code = Sapo SKU.
WITH products AS (
    SELECT
        product_key,
        product_name,
        sku                                                AS product_code
    FROM {{ ref('dim_products') }}
    WHERE product_key != {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
),

-- ----------------------------------------------------------------------------
-- Sales lines from fact_sales (Sapo order items)
-- Excludes: cancelled/voided orders, internal channels, Unknown products
-- ----------------------------------------------------------------------------
valid_channels AS (
    SELECT channel_key
    FROM {{ ref('dim_channels') }}
    WHERE is_sales_channel = true
),

sales_base AS (
    SELECT
        fs.product_key,
        fs.order_id,
        fs.channel_key,
        DATE_TRUNC('month', fs.ordered_at)::date AS snapshot_month,
        DATE(fs.ordered_at)                       AS sale_date,
        fs.quantity,
        fs.net_revenue                               AS line_revenue
    FROM {{ ref('fact_sales') }} fs
    -- Only sales channels (no internal / system)
    INNER JOIN valid_channels vc ON fs.channel_key = vc.channel_key
    -- Date range: 24 months back
    WHERE fs.ordered_at >= DATE_TRUNC('month', current_date) - INTERVAL '24 months'
      AND fs.ordered_at <  DATE_TRUNC('month', current_date)
      -- Exclude Unknown product
      AND fs.product_key != {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
      -- Revenue > 0 excludes gift/promo items at fact_sales level
      AND fs.net_revenue > 0
),

-- Order-level status filter: exclude cancelled orders
valid_orders AS (
    SELECT order_id
    FROM {{ ref('fact_orders') }}
    WHERE status != 'CANCELLED'
),

sales_filtered AS (
    SELECT sb.*
    FROM sales_base sb
    INNER JOIN valid_orders vo ON sb.order_id = vo.order_id
),

-- ----------------------------------------------------------------------------
-- Sales aggregates per (product_key, snapshot_month)
-- ----------------------------------------------------------------------------
sales_agg AS (
    SELECT
        product_key,
        snapshot_month,

        -- Volume
        SUM(quantity)                                           AS units_sold,
        SUM(line_revenue)                                       AS net_revenue,
        COUNT(DISTINCT order_id)                                AS order_count,

        -- Velocity inputs
        COUNT(DISTINCT sale_date)                               AS days_with_sales,
        MAX(sale_date)                                          AS last_sale_date
    FROM sales_filtered
    GROUP BY product_key, snapshot_month
),

-- Total monthly revenue across all SKUs (for revenue_share_pct)
monthly_totals AS (
    SELECT
        snapshot_month,
        SUM(net_revenue) AS total_month_revenue
    FROM sales_agg
    GROUP BY snapshot_month
),

-- Top-200 revenue threshold per month (for is_slow_mover)
top200_threshold AS (
    SELECT
        snapshot_month,
        MIN(net_revenue) AS threshold_revenue
    FROM (
        SELECT
            snapshot_month,
            net_revenue,
            ROW_NUMBER() OVER (
                PARTITION BY snapshot_month
                ORDER BY net_revenue DESC
            ) AS rn
        FROM sales_agg
    ) ranked
    WHERE rn <= 200
    GROUP BY snapshot_month
),

-- Returns from int_return_sku_lines, aggregated to (product_key, month)
returns_agg AS (
    SELECT
        r.product_key,
        DATE_TRUNC('month', r.return_date)::date               AS snapshot_month,

        COUNT(DISTINCT r.return_id)                             AS return_count,
        SUM(r.sold_quantity)                                    AS return_quantity,
        SUM(r.refund_amount_allocated)                          AS refund_amount_allocated
    FROM {{ ref('int_return_sku_lines') }} r
    WHERE r.return_date >= DATE_TRUNC('month', current_date) - INTERVAL '24 months'
      AND r.return_date <  DATE_TRUNC('month', current_date)
    GROUP BY r.product_key, DATE_TRUNC('month', r.return_date)::date
),

-- Top channel per (product_key, snapshot_month): channel with the highest revenue
channel_revenue AS (
    SELECT
        sf.product_key,
        sf.snapshot_month,
        sf.channel_key,
        SUM(sf.line_revenue) AS channel_revenue
    FROM sales_filtered sf
    GROUP BY sf.product_key, sf.snapshot_month, sf.channel_key
),

channel_ranked AS (
    SELECT
        cr.product_key,
        cr.snapshot_month,
        cr.channel_key,
        cr.channel_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY cr.product_key, cr.snapshot_month
            ORDER BY cr.channel_revenue DESC
        ) AS rn,
        SUM(cr.channel_revenue) OVER (
            PARTITION BY cr.product_key, cr.snapshot_month
        ) AS total_sku_channel_revenue
    FROM channel_revenue cr
),

top_channel AS (
    SELECT
        cr.product_key,
        cr.snapshot_month,
        dc.channel_name                                         AS top_channel_name,
        ROUND(
            cr.channel_revenue * 100.0
            / NULLIF(cr.total_sku_channel_revenue, 0),
            2
        )                                                       AS top_channel_revenue_pct
    FROM channel_ranked cr
    LEFT JOIN {{ ref('dim_channels') }} dc ON cr.channel_key = dc.channel_key
    WHERE cr.rn = 1
)

SELECT
    -- Identity
    sa.product_key,
    p.product_code,
    p.product_name,
    sa.snapshot_month,

    -- Revenue & Volume
    sa.units_sold,
    sa.net_revenue,
    sa.order_count,
    ROUND(
        sa.units_sold::double / NULLIF(sa.days_with_sales, 0),
        4
    )                                                       AS daily_velocity,

    -- Returns
    COALESCE(ra.return_count, 0)                            AS return_count,
    COALESCE(ra.return_quantity, 0)                         AS return_quantity,
    COALESCE(ra.refund_amount_allocated, 0)                 AS refund_amount_allocated,
    ROUND(
        COALESCE(ra.return_count, 0)::double
        / NULLIF(sa.order_count, 0),
        4
    )                                                       AS return_rate,

    -- Operational
    -- days_since_last_sale: days from snapshot month-end to last observed sale
    DATE_DIFF(
        'day',
        sa.last_sale_date,
        (sa.snapshot_month + INTERVAL '1 month' - INTERVAL '1 day')::date
    )                                                       AS days_since_last_sale,
    -- is_slow_mover: no sale in final 14 days of month AND not a top-200 SKU (caveat 2)
    (
        DATE_DIFF(
            'day',
            sa.last_sale_date,
            (sa.snapshot_month + INTERVAL '1 month' - INTERVAL '1 day')::date
        ) > 14
        AND sa.net_revenue < COALESCE(t200.threshold_revenue, 0)
    )                                                       AS is_slow_mover,
    ROUND(
        sa.net_revenue * 100.0
        / NULLIF(mt.total_month_revenue, 0),
        4
    )                                                       AS revenue_share_pct,

    -- Channel Concentration
    tc.top_channel_name,
    tc.top_channel_revenue_pct

FROM sales_agg sa
INNER JOIN products p          ON sa.product_key = p.product_key
LEFT  JOIN returns_agg ra      ON sa.product_key = ra.product_key
                              AND sa.snapshot_month = ra.snapshot_month
LEFT  JOIN monthly_totals mt   ON sa.snapshot_month = mt.snapshot_month
LEFT  JOIN top200_threshold t200 ON sa.snapshot_month = t200.snapshot_month
LEFT  JOIN top_channel tc      ON sa.product_key = tc.product_key
                              AND sa.snapshot_month = tc.snapshot_month
ORDER BY snapshot_month DESC, net_revenue DESC

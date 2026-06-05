{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Per-order profitability: Sapo revenue + MISA COGS + Shopee platform fees + fulfillment + returns.
-- Grain: one row per order (from fact_orders).
-- MISA lines aggregated to order level via voucher_no = order_code.
-- Shopee fees joined via order_code.
-- Returns are reference columns only — not restated into channel_net_profit (recognized at return date).

WITH orders AS (
    SELECT
        order_id,
        order_code,
        channel_key,
        date_key,
        status,
        gross_revenue,
        discount_amount,
        net_revenue,
        vat_amount,
        total_collected
    FROM {{ ref('fact_orders') }}
),

-- Aggregate MISA invoice lines to order level
misa_order AS (
    SELECT
        voucher_no AS order_code,
        SUM(cogs_amount)              AS cogs_amount,
        SUM(revenue_net_of_discount)  AS misa_revenue,
        SUM(gross_profit)             AS misa_gross_profit,
        COUNT(*)                      AS misa_line_count
    FROM {{ ref('int_misa_sales_lines') }}
    -- BUG-1: only TK632 = true COGS; exclude TK642 promo-goods (counted as promo cost, not COGS)
    WHERE cogs_account LIKE '632%'
    GROUP BY voucher_no
),

-- Shopee platform fees (already order-level)
shopee_fees AS (
    SELECT
        order_code,
        total_platform_fees,
        infrastructure_fee,
        voucher_xtra_fee,
        total_taxes      AS shopee_taxes,
        net_settlement
    FROM {{ ref('int_shopee_order_fees') }}
),

-- Primary shipment per order (earliest created_at) for carrier/COD info
fulfillments AS (
    SELECT order_id, cod_amount, carrier_id
    FROM {{ ref('std_fulfillments') }}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY created_at) = 1
),

-- Returns aggregated to order level (reference only — not subtracted from profit)
order_returns AS (
    SELECT
        order_code,
        SUM(refund_amount) AS return_amount,
        COUNT(*)           AS return_count
    FROM {{ ref('fact_order_returns') }}
    GROUP BY order_code
),

-- Promo goods cost — revenue=0 gift lines valued at Sapo-MAC (phase-03)
order_promo AS (
    SELECT
        order_code,
        SUM(promo_goods_cost_amount) AS promo_goods_cost
    FROM {{ ref('int_order_promo_goods_cost') }}
    GROUP BY order_code
),

-- Overhead allocation aggregated to order level (phase-04)
order_overhead AS (
    SELECT order_code,
           SUM(allocated_amount)          AS allocated_overhead,
           BOOL_OR(is_overhead_estimated) AS is_overhead_estimated
    FROM {{ ref('int_order_overhead_allocation') }}
    GROUP BY order_code
)

SELECT
    -- Keys (inherit from fact_orders)
    o.order_id,
    o.order_code,
    o.channel_key,
    o.date_key,
    o.status,

    -- Revenue (from Sapo)
    o.gross_revenue,
    o.discount_amount,
    o.net_revenue,
    o.vat_amount,
    o.total_collected,

    -- COGS (from MISA)
    m.cogs_amount,
    m.misa_line_count,
    m.cogs_amount IS NOT NULL AS has_cogs,

    -- Promo goods cost (revenue=0 gift lines; marketing cost, NOT COGS — phase-03)
    pg.promo_goods_cost,

    -- Gross Profit = Net Revenue - COGS
    o.net_revenue - COALESCE(m.cogs_amount, 0) AS gross_profit,

    -- Gross Margin %
    CASE
        WHEN o.net_revenue = 0 THEN NULL
        ELSE (o.net_revenue - COALESCE(m.cogs_amount, 0))::DOUBLE / o.net_revenue
    END AS gross_margin_pct,

    -- Shopee platform economics (NULL for non-Shopee orders)
    -- shopee_platform_fees = total_platform_fees (payment/fixed/affiliate/piship) + infra + voucher_xtra.
    -- service_fee (D-aggregate) was removed upstream (phase-07: it equalled infra+voucher_xtra → double-count).
    -- F-detail rows (infra + voucher_xtra) are now the sole service-fee source; sum is non-duplicated.
    CASE WHEN sf.order_code IS NOT NULL
        THEN sf.total_platform_fees
             + COALESCE(sf.infrastructure_fee, 0)
             + COALESCE(sf.voucher_xtra_fee, 0)
        ELSE NULL
    END                     AS shopee_platform_fees,
    sf.infrastructure_fee   AS shopee_infra_fee,
    sf.voucher_xtra_fee     AS shopee_voucher_xtra_fee,
    sf.shopee_taxes,
    sf.net_settlement       AS shopee_net_settlement,
    sf.order_code IS NOT NULL AS has_platform_fees,

    -- Channel Net Profit = Net Revenue - COGS - |Shopee fees| - |Shopee taxes|
    -- For non-Shopee orders: same as gross_profit
    o.net_revenue
        - COALESCE(m.cogs_amount, 0)
        + COALESCE(sf.total_platform_fees, 0)   -- negative values from Shopee
        + COALESCE(sf.infrastructure_fee, 0)
        + COALESCE(sf.voucher_xtra_fee, 0)
        + COALESCE(sf.shopee_taxes, 0)
        AS channel_net_profit,

    -- Channel Net Margin %
    CASE
        WHEN o.net_revenue = 0 THEN NULL
        ELSE (
            o.net_revenue
            - COALESCE(m.cogs_amount, 0)
            + COALESCE(sf.total_platform_fees, 0)
            + COALESCE(sf.infrastructure_fee, 0)
            + COALESCE(sf.voucher_xtra_fee, 0)
            + COALESCE(sf.shopee_taxes, 0)
        )::DOUBLE / o.net_revenue
    END AS channel_net_margin_pct,

    -- Tier-3 (REPORT only): allocated overhead → fully-loaded net profit. NOT for accept/reject (use channel_net_profit). phase-04
    oh.allocated_overhead,
    COALESCE(oh.is_overhead_estimated, FALSE) AS is_overhead_estimated,
    CASE
        WHEN oh.allocated_overhead IS NOT NULL
        THEN o.net_revenue
                - COALESCE(m.cogs_amount, 0)
                + COALESCE(sf.total_platform_fees, 0)
                + COALESCE(sf.infrastructure_fee, 0)
                + COALESCE(sf.voucher_xtra_fee, 0)
                + COALESCE(sf.shopee_taxes, 0)
                - oh.allocated_overhead
        ELSE NULL
    END AS fully_loaded_net_profit,
    CASE
        WHEN o.net_revenue = 0 OR oh.allocated_overhead IS NULL THEN NULL
        ELSE (
            o.net_revenue
            - COALESCE(m.cogs_amount, 0)
            + COALESCE(sf.total_platform_fees, 0)
            + COALESCE(sf.infrastructure_fee, 0)
            + COALESCE(sf.voucher_xtra_fee, 0)
            + COALESCE(sf.shopee_taxes, 0)
            - oh.allocated_overhead
        )::DOUBLE / o.net_revenue
    END AS fully_loaded_margin_pct,

    -- Fulfillment (primary shipment)
    ff.cod_amount,
    ff.carrier_id,

    -- Returns (reference only — P&L impact recognized in fact_order_returns at return date)
    r.return_amount,
    COALESCE(r.return_count, 0) AS return_count,
    COALESCE(r.return_count, 0) > 0 AS has_returns

FROM orders o
LEFT JOIN misa_order m    ON o.order_code = m.order_code
LEFT JOIN shopee_fees sf  ON o.order_code = sf.order_code
LEFT JOIN fulfillments ff ON o.order_id   = ff.order_id
LEFT JOIN order_returns r ON o.order_code = r.order_code
LEFT JOIN order_promo pg  ON o.order_code = pg.order_code
LEFT JOIN order_overhead oh ON o.order_code = oh.order_code

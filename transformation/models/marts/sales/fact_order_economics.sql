{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Per-order profitability: Sapo revenue + MISA COGS + Shopee platform fees.
-- Grain: one row per order (from fact_orders).
-- MISA lines aggregated to order level via voucher_no = order_code.
-- Shopee fees joined via order_code.

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
        tax_amount,
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
    o.tax_amount,
    o.total_collected,

    -- COGS (from MISA)
    m.cogs_amount,
    m.misa_line_count,
    m.cogs_amount IS NOT NULL AS has_cogs,

    -- Gross Profit = Net Revenue - COGS
    o.net_revenue - COALESCE(m.cogs_amount, 0) AS gross_profit,

    -- Gross Margin %
    CASE
        WHEN o.net_revenue = 0 THEN NULL
        ELSE (o.net_revenue - COALESCE(m.cogs_amount, 0))::DOUBLE / o.net_revenue
    END AS gross_margin_pct,

    -- Shopee platform economics (NULL for non-Shopee orders)
    sf.total_platform_fees  AS shopee_platform_fees,
    sf.infrastructure_fee   AS shopee_infra_fee,
    sf.voucher_xtra_fee     AS shopee_voucher_xtra_fee,
    sf.shopee_taxes,
    sf.net_settlement       AS shopee_net_settlement,
    sf.order_code IS NOT NULL AS has_shopee_fees,

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
    END AS channel_net_margin_pct

FROM orders o
LEFT JOIN misa_order m ON o.order_code = m.order_code
LEFT JOIN shopee_fees sf ON o.order_code = sf.order_code

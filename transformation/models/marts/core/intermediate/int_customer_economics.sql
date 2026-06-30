{{ config(
    materialized='table',
    tags=['mart', 'intermediate']
) }}

-- Customer-level contribution margin aggregation.
-- Grain: one row per customer_key.
-- Contribution = channel_net_profit (gross_profit − Shopee platform fees; no overhead).
-- See fact_order_economics: channel_net_profit excludes allocated_overhead by design.
-- Only orders where has_cogs=TRUE contribute to lifetime_gross_profit / lifetime_contribution_margin
-- (orders without COGS are unreliable for margin; counted in denominator for coverage metric only).

WITH order_economics AS (
    SELECT
        fo.customer_key,
        foe.order_id,
        foe.gross_profit,
        foe.channel_net_profit,     -- contribution: gross_profit − direct Shopee fees, no overhead
        foe.net_revenue,
        foe.has_cogs,
        foe.is_active_order,
        foe.gross_margin_pct,
        foe.cogs_amount,
        foe.return_amount,
        foe.return_count
    FROM {{ ref('fact_order_economics') }} foe
    JOIN {{ ref('fact_orders') }} fo ON foe.order_id = fo.order_id
    WHERE foe.is_active_order
),

customer_economics AS (
    SELECT
        oe.customer_key,

        -- Lifetime gross profit (has_cogs orders only — unreliable without cost data)
        SUM(oe.gross_profit) FILTER (WHERE oe.has_cogs)::BIGINT         AS lifetime_gross_profit,

        -- Lifetime contribution margin = Σ channel_net_profit (has_cogs only)
        -- channel_net_profit = gross_profit − Shopee platform fees (zero for non-Shopee)
        -- Excludes allocated_overhead → pure contribution margin per business decision
        SUM(oe.channel_net_profit) FILTER (WHERE oe.has_cogs)::BIGINT   AS lifetime_contribution_margin,

        -- Per-order contribution margin % averaged across active orders
        -- NULLIF guards against net_revenue=0 (fully-discounted/gift orders)
        AVG(
            oe.channel_net_profit / NULLIF(oe.net_revenue, 0)
        )::DOUBLE                                                         AS avg_order_contribution_margin_pct,

        -- COGS coverage: share of active orders that have COGS data (caveat metric)
        -- Indicates how reliable the margin figures are for this customer
        (COUNT(*) FILTER (WHERE oe.has_cogs))::DOUBLE
            / NULLIF(COUNT(*), 0)                                         AS margin_cogs_coverage_pct,

        -- Negative lifetime contribution flag
        -- NULL when no has_cogs orders (no margin data at all)
        CASE
            WHEN COUNT(*) FILTER (WHERE oe.has_cogs) = 0 THEN NULL
            ELSE SUM(oe.channel_net_profit) FILTER (WHERE oe.has_cogs) < 0
        END                                                               AS is_margin_negative,

        -- Pre-computed profitability/returns metrics (pre-compute here; exposed via dim_customers)
        SUM(oe.cogs_amount) FILTER (WHERE oe.has_cogs)::BIGINT           AS total_cogs,
        AVG(oe.gross_margin_pct) FILTER (WHERE oe.has_cogs)              AS avg_gross_margin_pct,
        -- No has_cogs filter for returns — returns can occur on any order
        SUM(oe.return_amount)::BIGINT                                     AS total_return_amount,
        SUM(oe.return_count)::INTEGER                                     AS return_count,
        COUNT(*) FILTER (WHERE oe.has_cogs)::INTEGER                     AS cogs_order_count,

        current_timestamp                                                 AS metric_calculated_at

    FROM order_economics oe
    GROUP BY oe.customer_key
)

SELECT
    customer_key,
    lifetime_gross_profit,
    lifetime_contribution_margin,
    avg_order_contribution_margin_pct,
    margin_cogs_coverage_pct,
    is_margin_negative,
    total_cogs,
    avg_gross_margin_pct,
    total_return_amount,
    return_count,
    cogs_order_count,
    metric_calculated_at
FROM customer_economics

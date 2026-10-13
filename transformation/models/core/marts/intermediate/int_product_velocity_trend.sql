{{ config(
    materialized='table',
    tags=['mart', 'intermediate']
) }}

-- Product-level velocity trend and lifecycle dates.
-- Grain: one row per product_key (all SKUs present in mart_sku_economics_monthly).
-- velocity_90d  = avg daily_velocity over the trailing 3 monthly snapshots (approx. 90 days).
-- velocity_30d  = daily_velocity of the single latest snapshot month.
-- velocity_momentum = comparison of 30d vs 90d rate; NULL when < 3 trailing months are available.
-- Source: mart_sku_economics_monthly (24-month rolling window, grain: product_key × snapshot_month).
-- Downstream: mart_product_health (G3 momentum + G4 lifecycle inputs).

WITH latest_month AS (
    -- Determine the most-recent snapshot month at query time — never hardcode a date.
    SELECT MAX(snapshot_month) AS max_month
    FROM {{ ref('mart_sku_economics_monthly') }}
),

-- Trailing 3 months = latest_month − 2 months through latest_month (≈ 90 calendar days).
-- Uses INTERVAL arithmetic so the window always shifts with the data.
trailing_3m AS (
    SELECT
        m.product_key,
        m.snapshot_month,
        m.daily_velocity
    FROM {{ ref('mart_sku_economics_monthly') }} m
    CROSS JOIN latest_month lm
    WHERE m.snapshot_month >= lm.max_month - INTERVAL 2 MONTH
),

velocity_agg AS (
    SELECT
        product_key,

        -- 90-day proxy: average of up to 3 monthly snapshots
        AVG(daily_velocity)::DOUBLE                                         AS velocity_90d,

        -- 30-day proxy: velocity of the latest snapshot month only
        -- FILTER ensures we pick the single latest-month row per product;
        -- NULL when the product has no row in the latest month (inactive that month).
        MAX(daily_velocity) FILTER (
            WHERE snapshot_month = (SELECT max_month FROM latest_month)
        )::DOUBLE                                                            AS velocity_30d,

        -- Track how many trailing months exist to gate momentum classification
        COUNT(*)::INT                                                        AS trailing_months

    FROM trailing_3m
    GROUP BY product_key
),

first_sale AS (
    -- Lifecycle anchors — computed over the full 24-month history, not just the trailing window.
    SELECT
        product_key,
        MIN(snapshot_month)                                                  AS first_sale_month,
        COUNT(CASE WHEN units_sold > 0 THEN 1 END)::INT                     AS months_active
    FROM {{ ref('mart_sku_economics_monthly') }}
    GROUP BY product_key
)

SELECT
    va.product_key,

    -- Velocity metrics
    va.velocity_90d,
    va.velocity_30d,

    -- Momentum classification (NULL = insufficient trailing history, < 3 months)
    -- Thresholds: >+15% → ACCELERATING; <−15% → DECELERATING; else STABLE.
    -- Matches spec §3 / product.md metric #16 (velocity_momentum).
    CASE
        WHEN va.trailing_months < 3                          THEN NULL
        WHEN va.velocity_30d > va.velocity_90d * 1.15       THEN 'ACCELERATING'
        WHEN va.velocity_30d < va.velocity_90d * 0.85       THEN 'DECELERATING'
        ELSE 'STABLE'
    END                                                                      AS velocity_momentum,

    -- Lifecycle anchor dates
    fs.first_sale_month,
    fs.months_active

FROM velocity_agg va
-- All products in sku_economics have first_sale data — INNER JOIN is safe here.
JOIN first_sale fs ON va.product_key = fs.product_key

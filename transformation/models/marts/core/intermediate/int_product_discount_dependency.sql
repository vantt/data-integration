{{ config(
    materialized='table',
    tags=['mart', 'intermediate']
) }}

-- Product-level discount dependency classification.
-- Grain: one row per product_key (all products ever appearing in fact_sales).
-- discount_share = SUM(discount_amount) / SUM(gross_proxy)
--   where gross_proxy = net_revenue + discount_amount
--   (net_revenue is VAT-exclusive; adding back discount_amount recovers the pre-discount line price).
-- discount_dependency is NULL when a product has no gross_proxy (zero-revenue + zero-discount rows).
-- Source: fact_sales (full history, all order statuses present in the mart).
-- Downstream: mart_product_health (G5 discount_dependency input).
-- Matches spec §3 / product.md metric #18 (discount_dependency).

SELECT
    product_key,

    -- Discount as share of gross (pre-discount) revenue.
    -- NULLIF guards against zero-gross edge case (fully-discounted gift lines with zero net_revenue).
    (
        SUM(discount_amount) /
        NULLIF(SUM(net_revenue + discount_amount), 0)
    )::DOUBLE                                                                AS discount_share,

    -- Classification: NULL when no sales data (discount_share IS NULL).
    -- PROMO_HEAVY >40% of gross is discount — margin erosion risk.
    -- PROMO_LIGHT  >10% — occasional promotion use.
    -- FULL_PRICE  ≤10% — predominantly sold at full price.
    CASE
        WHEN SUM(net_revenue + discount_amount) IS NULL
          OR SUM(net_revenue + discount_amount) = 0                         THEN NULL
        WHEN SUM(discount_amount) /
             NULLIF(SUM(net_revenue + discount_amount), 0) > 0.4            THEN 'PROMO_HEAVY'
        WHEN SUM(discount_amount) /
             NULLIF(SUM(net_revenue + discount_amount), 0) > 0.1            THEN 'PROMO_LIGHT'
        ELSE 'FULL_PRICE'
    END                                                                      AS discount_dependency

FROM {{ ref('fact_sales') }}
GROUP BY product_key

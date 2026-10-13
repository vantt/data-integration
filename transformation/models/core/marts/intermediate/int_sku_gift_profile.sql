{{ config(
    materialized='table',
    tags=['mart', 'intermediate']
) }}

-- =============================================================================
-- INTERMEDIATE: SKU GIFT-RATE PROFILE
-- =============================================================================
-- Grain: one row per SKU (ALL SKUs ever sold — not limited to the 8 core SKUs
-- in seed_sku_regimen_config; consumers filter down where needed).
--
-- gift_rate = share of line items where line_amount = 0 (fact_sales.is_gift_line,
-- computed in Phase 1). Distinguishes anchor/premium SKUs (customer actively buys)
-- from entry/gift-prone SKUs (frequently bundled in free with a paid item).
--
-- multi_sku_gift_rate splits this further by basket composition: per the
-- finejapan gift-entry-sku report, gift-rate differs sharply between solo-SKU
-- and multi-SKU orders (a SKU can look gift-heavy overall but is actually only
-- gifted when bundled with other SKUs in the same basket).
--
-- Deliberately NOT exposing a hardcoded sku_role threshold label here — see
-- schema.yml doc + plans/260708-1501-gift-purchase-sku-action-scenario/plan.md
-- open question #2. Consumers (Phase 4 action queue) apply their own threshold
-- on gift_rate / multi_sku_gift_rate.
-- =============================================================================

WITH lines AS (
    SELECT
        dp.sku,
        fs.is_gift_line,
        -- Multi-SKU basket flag: per finejapan report, gift-rate differs sharply
        -- solo vs multi-SKU orders. Expose both for transparency.
        COUNT(*) OVER (PARTITION BY fs.order_id) > 1 AS is_multi_sku_basket
    FROM {{ ref('fact_sales') }} fs
    JOIN {{ ref('dim_products') }} dp ON fs.product_key = dp.product_key
    JOIN {{ ref('fact_orders') }} fo ON fs.order_id = fo.order_id
    WHERE fo.is_active_order = TRUE
)

SELECT
    sku,
    COUNT(*)                                              AS total_lines,
    COUNT(*) FILTER (WHERE is_gift_line)                  AS gift_lines,
    ROUND(COUNT(*) FILTER (WHERE is_gift_line)::DOUBLE / NULLIF(COUNT(*), 0), 4) AS gift_rate,
    COUNT(*) FILTER (WHERE is_multi_sku_basket)                                   AS multi_sku_lines,
    COUNT(*) FILTER (WHERE is_multi_sku_basket AND is_gift_line)                  AS multi_sku_gift_lines,
    ROUND(
        COUNT(*) FILTER (WHERE is_multi_sku_basket AND is_gift_line)::DOUBLE
        / NULLIF(COUNT(*) FILTER (WHERE is_multi_sku_basket), 0), 4
    )                                                      AS multi_sku_gift_rate
FROM lines
GROUP BY sku

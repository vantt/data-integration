{{ config(
    tags=['mart', 'fact', 'us_shipment'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- US CrossBorder order economics — actual revenue from the US Shipment Price List.
-- Grain: one row per US order (order_id).
-- Source: int_us_shipment_line_prices aggregated to order level.
--
-- Why a separate mart (not mutating fact_order_economics):
--   US pricing logic is channel-specific; keeping it isolated avoids contaminating
--   the shared fact_order_economics with US-only join paths.
--
-- has_unpriced_sku=TRUE means at least one line item had no matching price —
-- total_us_revenue figures will be understated for that order.

WITH line_prices AS (
    SELECT * FROM {{ ref('int_us_shipment_line_prices') }}
)

SELECT
    order_id,
    order_code,
    channel_key,
    date_key,

    -- Actual US deal revenue (excl. 8% VAT) — primary reporting metric
    SUM(line_revenue_excl_vat)                           AS total_us_revenue_excl_vat,

    -- Actual US deal revenue incl. 8% VAT — for VAT reporting
    SUM(line_revenue_incl_vat)                           AS total_us_revenue_incl_vat,

    -- Line item count
    COUNT(*)                                             AS line_item_count,

    -- Data quality flag: TRUE if any line had no price in the price list
    BOOL_OR(is_price_missing)                            AS has_unpriced_sku,

    -- Count of unpriced lines for debugging
    COUNT_IF(is_price_missing)                           AS unpriced_sku_count

FROM line_prices
GROUP BY order_id, order_code, channel_key, date_key

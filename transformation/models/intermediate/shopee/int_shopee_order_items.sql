{{ config(
    tags=['int', 'shopee'],
    materialized='table',
    location="{{ get_rolling_location() }}"
) }}

-- Shopee per-order × product line items.
-- Joins to int_shopee_order_fees for temporal and settlement context.

SELECT
    {{ dbt_utils.generate_surrogate_key(['items.order_code', 'items.product_code']) }} AS shopee_order_item_sk,
    items.order_code,
    items.product_code,
    items.product_name,
    orders.payout_released_at,
    orders.order_placed_at,
    orders.net_settlement,
    items.source_file,
    items.ingested_at

FROM {{ ref('stg_shopee_order_revenue_items') }} items
INNER JOIN {{ ref('int_shopee_order_fees') }} orders USING (order_code)

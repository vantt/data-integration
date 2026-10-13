{{ config(materialized='view', tags=['staging', 'sapo']) }}

-- Unnest discount_items array from deduplicated Sapo orders.
-- Grain: 1 row per discount item per order.
-- Reads from src_sapo_orders (not raw source) to avoid Delta Lake ghost-file multiplication.
-- B2B wholesale-price-gap rows (reason='', rate=100) are excluded here.
-- Downstream: used by fact_order_costs to classify discount cost_types.

WITH raw AS (
    SELECT
        order_id,
        order_code,
        TRY_CAST(created_on AS TIMESTAMPTZ) AS created_at,
        discount_items_json
    FROM {{ ref('src_sapo_v2_orders') }}
    WHERE json_array_length(discount_items_json) > 0
),

unnested AS (
    SELECT
        order_id,
        order_code,
        created_at,
        UNNEST(
            FROM_JSON(
                discount_items_json,
                '[{"source": "VARCHAR", "rate": "DOUBLE", "value": "DOUBLE",
                   "amount": "DOUBLE", "reason": "VARCHAR",
                   "promotion_redemption_id": "VARCHAR",
                   "promotion_condition_item_id": "VARCHAR"}]'
            )
        ) AS item
    FROM raw
)

SELECT
    order_id,
    order_code,
    created_at,
    item.source    AS discount_source,
    item.rate      AS discount_rate,
    item.value     AS discount_value,
    TRY_CAST(item.amount AS DECIMAL(18, 2)) AS amount,
    item.reason    AS reason
FROM unnested
-- Keep only rows with a real monetary amount
WHERE TRY_CAST(item.amount AS DECIMAL(18, 2)) > 0
  -- Skip B2B wholesale price-gap entries (rate=100, empty reason)
  AND NOT (COALESCE(item.reason, '') = '' AND item.rate = 100.0)

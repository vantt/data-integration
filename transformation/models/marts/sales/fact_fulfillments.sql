{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Per-shipment fact: one row per Sapo fulfillment (shipment leg).
-- Source: std_fulfillments (Hop 5, standardized). order_code resolved via fact_orders.order_id
-- (order_id type differs across models — cast both sides to VARCHAR before joining).
-- Powers: order lookup by shipment code / id / tracking code, and the Shipments
-- section of the detailView Operations tab. Grain enforced unique on fulfillment_id.

WITH fulfillments AS (
    SELECT * FROM {{ ref('std_fulfillments') }}
),

order_codes AS (
    SELECT order_id, order_code FROM {{ ref('fact_orders') }}
)

SELECT
    f.fulfillment_id,
    f.fulfillment_code,
    f.order_id,
    oc.order_code,
    f.tracking_code,
    f.carrier_id,
    f.shipping_service,
    f.status,
    f.cod_amount,
    f.created_at,
    f.shipped_at
FROM fulfillments f
LEFT JOIN order_codes oc
    ON CAST(f.order_id AS VARCHAR) = CAST(oc.order_id AS VARCHAR)
-- Guard grain: keep the latest row per fulfillment_id so the unique test holds
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY f.fulfillment_id
    ORDER BY f.shipped_at DESC NULLS LAST, f.created_at DESC NULLS LAST
) = 1

{{ config(
    tags=['int', 'us_shipment'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Enrich US CrossBorder order line items with actual deal prices from the price list.
-- Sapo records US shipment net_revenue=0; this model computes the real per-line revenue.
-- Grain: one row per order line item (order_id × order_line_id).
--
-- Join logic: for each line item, find the price row where
--   sku matches AND effective_from <= order_date
-- then take the latest effective_from (QUALIFY ROW_NUMBER).
-- If no price exists for a SKU, the row is kept with NULL prices (is_price_missing=TRUE).

WITH us_orders AS (
    SELECT
        o.order_id,
        o.order_code,
        o.channel_key,
        o.date_key,
        o.order_timestamp
    FROM {{ ref('fact_orders') }} o
    JOIN {{ ref('dim_channels') }} ch ON o.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      AND o.status NOT IN ('CANCELLED', 'Voided')
),

order_items AS (
    SELECT
        i.order_line_id,
        i.order_id,
        upper(trim(cast(i.sku as varchar))) AS sku,
        i.quantity
    FROM {{ ref('std_order_items') }} i
    INNER JOIN us_orders o ON i.order_id = o.order_id
),

prices AS (
    SELECT
        sku,
        us_price_excl_vat,
        us_price_incl_vat,
        effective_from
    FROM {{ ref('stg_us_shipment_prices') }}
)

SELECT
    oi.order_line_id,
    oi.order_id,
    uo.order_code,
    uo.channel_key,
    uo.date_key,
    oi.sku,
    oi.quantity,
    p.us_price_excl_vat,
    p.us_price_incl_vat,
    p.effective_from                                      AS price_effective_from,
    oi.quantity * p.us_price_excl_vat                    AS line_revenue_excl_vat,
    oi.quantity * p.us_price_incl_vat                    AS line_revenue_incl_vat,
    p.us_price_excl_vat IS NULL                          AS is_price_missing

FROM order_items oi
JOIN us_orders uo ON oi.order_id = uo.order_id
LEFT JOIN prices p
    ON p.sku = oi.sku
    AND p.effective_from <= cast(uo.order_timestamp AS date)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY oi.order_line_id
    ORDER BY p.effective_from DESC NULLS LAST
) = 1

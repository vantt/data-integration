{{ config(
    materialized='view',
    tags=['staging', 'us_shipment']
) }}

-- US Shipment Price List — one row per (SKU, effective_from).
-- Source sheet maintains history: add a new row per SKU when the price changes.
-- effective_from determines which price applies to a given order date.

WITH raw AS (
    SELECT * FROM {{ source('sapo_raw', 'us_shipment_prices_raw') }}
),

cleaned AS (
    SELECT
        upper(trim(cast(sku as varchar)))              AS sku,
        trim(cast(product_name as varchar))            AS product_name,
        cast(cost_price as decimal(15, 2))             AS cost_price,
        cast(us_price_excl_vat as decimal(15, 2))      AS us_price_excl_vat,
        cast(us_price_incl_vat as decimal(15, 2))      AS us_price_incl_vat,
        cast(retail_price as decimal(15, 2))           AS retail_price,
        cast(fg_care_price as decimal(15, 2))          AS fg_care_price,
        cast(margin_pct as decimal(8, 6))              AS margin_pct,
        cast(effective_from as date)                   AS effective_from,
        cast(ingest_method as varchar)                 AS ingest_method

    FROM raw
    WHERE sku IS NOT NULL
      AND trim(cast(sku as varchar)) != ''
      AND us_price_excl_vat > 0
      AND effective_from IS NOT NULL
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['sku', 'effective_from']) }} AS price_key,
    sku,
    product_name,
    cost_price,
    us_price_excl_vat,
    us_price_incl_vat,
    retail_price,
    fg_care_price,
    margin_pct,
    effective_from,
    ingest_method
FROM cleaned

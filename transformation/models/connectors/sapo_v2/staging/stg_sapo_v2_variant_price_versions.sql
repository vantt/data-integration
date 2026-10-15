{{ config(
    materialized='view',
    tags=['staging', 'products', 'prices', 'history']
) }}

-- =================================================================================================
-- STAGING: SAPO VARIANT PRICE VERSIONS (backfill of price history)
-- =================================================================================================
-- One row per (product version, variant, price list) from EVERY product payload ever loaded into
-- sapo_v2_raw/product (batch_sync since 28/05/2026, history_log for some products since 03/2026),
-- not deduplicated like src_sapo_v2_products. observed_at = event_timestamp of the version
-- (product modified_on for batch_sync). Used to backfill price intervals before the nightly capture
-- started; a price change Sapo made without moving modified_on is not visible here.
-- =================================================================================================

WITH versions AS (
    SELECT
        entity_id,
        ingest_method,
        _dlt_load_id,
        CAST(event_timestamp AS TIMESTAMPTZ)               AS observed_at,
        json_extract_string(payload, '$.id')               AS product_id,
        unnest(from_json(json_extract(payload, '$.variants'), '["JSON"]')) AS v
    FROM {{ source('sapo_v2_raw', 'product') }}
    WHERE event_timestamp IS NOT NULL
      AND json_array_length(json_extract(payload, '$.variants')) > 0
),

prices AS (
    SELECT
        entity_id,
        ingest_method,
        _dlt_load_id,
        observed_at,
        product_id,
        json_extract_string(v, '$.id')  AS variant_id,
        json_extract_string(v, '$.sku') AS sku,
        unnest(from_json(json_extract(v, '$.variant_prices'), '["JSON"]')) AS vp
    FROM versions
    WHERE json_array_length(json_extract(v, '$.variant_prices')) > 0
)

SELECT
    variant_id,
    product_id,
    sku,
    json_extract_string(vp, '$.price_list_id') AS price_list_id,
    json_extract_string(vp, '$.name') AS price_list_name,
    json_extract_string(vp, '$.price_list.code') AS price_list_code,
    CASE WHEN json_extract_string(vp, '$.price_list.is_cost') = 'true'
         THEN true ELSE false
    END AS is_cost_price,
    try_cast(json_extract_string(vp, '$.value') AS DECIMAL(18,2)) AS price_value,
    try_cast(json_extract_string(vp, '$.included_tax_price') AS DECIMAL(18,2)) AS price_incl_tax,
    observed_at,
    ingest_method,
    _dlt_load_id
FROM prices

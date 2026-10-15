{{ config(
    materialized='view',
    tags=['staging', 'products', 'prices', 'history']
) }}

-- =================================================================================================
-- STAGING: SAPO VARIANT PRICE CAPTURES
-- =================================================================================================
-- One row per (capture run, variant, price list) from the nightly full capture. Same columns and
-- parsing as stg_sapo_v2_variant_prices, plus captured_at and capture_run_id. Zero prices are
-- kept (value 0 = channel not configured for the SKU); the history marts flag them.
-- =================================================================================================

WITH variants AS (
    SELECT
        product_id,
        captured_at,
        capture_run_id,
        unnest(from_json(variants_json, '["JSON"]')) AS v
    FROM {{ ref('src_sapo_v2_product_daily_snapshots') }}
    WHERE variants_json IS NOT NULL
      AND variants_json NOT IN ('[]', 'null', '')
),

prices AS (
    SELECT
        product_id,
        captured_at,
        capture_run_id,
        json_extract_string(v, '$.id')  AS variant_id,
        json_extract_string(v, '$.sku') AS sku,
        unnest(from_json(json_extract(v, '$.variant_prices'), '["JSON"]')) AS vp
    FROM variants
    WHERE json_array_length(json_extract(v, '$.variant_prices')) > 0
)

SELECT
    variant_id,
    product_id,
    sku,

    -- Price list identification
    json_extract_string(vp, '$.price_list_id') AS price_list_id,
    json_extract_string(vp, '$.name') AS price_list_name,
    json_extract_string(vp, '$.price_list.code') AS price_list_code,
    CASE WHEN json_extract_string(vp, '$.price_list.is_cost') = 'true'
         THEN true ELSE false
    END AS is_cost_price,

    -- Price values
    try_cast(json_extract_string(vp, '$.value') AS DECIMAL(18,2)) AS price_value,
    try_cast(json_extract_string(vp, '$.included_tax_price') AS DECIMAL(18,2)) AS price_incl_tax,

    -- Capture
    captured_at,
    capture_run_id

FROM prices

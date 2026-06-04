{{ config(
    materialized='view',
    tags=['staging', 'products', 'prices']
) }}

-- =================================================================================================
-- STAGING: SAPO VARIANT PRICES
-- =================================================================================================
-- Purpose:
--   Unnest variant_prices_json from stg_sapo_variants into one row per
--   (variant_id, price_list_id). Extracts price value, price list metadata.
-- =================================================================================================

WITH source AS (
    SELECT
        variant_id,
        product_id,
        sku,
        variant_prices_json,
        source_timestamp
    FROM {{ ref('stg_sapo_variants_v2') }}
),

unnested AS (
    SELECT
        variant_id,
        product_id,
        sku,
        source_timestamp,
        unnest(from_json(variant_prices_json, '["JSON"]')) as vp
    FROM source
    WHERE variant_prices_json IS NOT NULL
      AND variant_prices_json NOT IN ('[]', 'null', '')
)

SELECT
    variant_id,
    product_id,
    sku,

    -- Price list identification
    json_extract_string(vp, '$.price_list_id') as price_list_id,
    json_extract_string(vp, '$.name') as price_list_name,
    json_extract_string(vp, '$.price_list.code') as price_list_code,
    CASE WHEN json_extract_string(vp, '$.price_list.is_cost') = 'true'
         THEN true ELSE false
    END as is_cost_price,

    -- Price values
    try_cast(json_extract_string(vp, '$.value') as DECIMAL(18,2)) as price_value,
    try_cast(json_extract_string(vp, '$.included_tax_price') as DECIMAL(18,2)) as price_incl_tax,

    -- Metadata
    source_timestamp

FROM unnested

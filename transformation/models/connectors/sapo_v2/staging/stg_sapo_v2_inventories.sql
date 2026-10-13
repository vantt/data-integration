{{ config(
    materialized='view',
    tags=['staging', 'products', 'inventory']
) }}

-- =================================================================================================
-- STAGING: SAPO INVENTORIES
-- =================================================================================================
-- Purpose:
--   Unnest inventories_json from stg_sapo_variants into one row per
--   (variant_id, location_id). Tracks on_hand, available, committed stock.
-- =================================================================================================

WITH source AS (
    SELECT
        variant_id,
        product_id,
        sku,
        inventories_json,
        source_timestamp
    FROM {{ ref('stg_sapo_v2_variants') }}
),

unnested AS (
    SELECT
        variant_id,
        product_id,
        sku,
        source_timestamp,
        unnest(from_json(inventories_json, '["JSON"]')) as inv
    FROM source
    WHERE inventories_json IS NOT NULL
      AND inventories_json NOT IN ('[]', 'null', '')
)

SELECT
    variant_id,
    product_id,
    sku,

    -- Location
    json_extract_string(inv, '$.location_id') as location_id,

    -- Stock levels
    try_cast(json_extract_string(inv, '$.on_hand') as DECIMAL(18,4)) as on_hand,
    try_cast(json_extract_string(inv, '$.available') as DECIMAL(18,4)) as available,
    try_cast(json_extract_string(inv, '$.committed') as DECIMAL(18,4)) as committed,
    try_cast(json_extract_string(inv, '$.incoming') as DECIMAL(18,4)) as incoming,
    try_cast(json_extract_string(inv, '$.onway') as DECIMAL(18,4)) as onway,

    -- MAC (Moving Average Cost)
    try_cast(json_extract_string(inv, '$.mac') as DECIMAL(18,4)) as mac,

    -- Bin location
    json_extract_string(inv, '$.bin_location') as bin_location,

    -- Metadata
    try_cast(json_extract_string(inv, '$.modified_on') AS TIMESTAMPTZ) as inventory_modified_at,
    source_timestamp

FROM unnested

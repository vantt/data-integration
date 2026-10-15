{{ config(
    materialized='view',
    tags=['staging', 'inventory', 'history']
) }}

-- =================================================================================================
-- STAGING: SAPO INVENTORY POSITION CAPTURES
-- =================================================================================================
-- One row per (capture run, variant, location) from the nightly full capture: the stock position
-- Sapo reported at captured_at. Same parsing and types as int_sapo_inventories.
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

inventories AS (
    SELECT
        product_id,
        captured_at,
        capture_run_id,
        json_extract_string(v, '$.id')  AS variant_id,
        json_extract_string(v, '$.sku') AS sku,
        unnest(from_json(json_extract(v, '$.inventories'), '["JSON"]')) AS inv
    FROM variants
    WHERE json_array_length(json_extract(v, '$.inventories')) > 0
)

SELECT
    variant_id,
    product_id,
    sku,
    json_extract_string(inv, '$.location_id')                                AS location_id,

    -- Stock levels
    try_cast(json_extract_string(inv, '$.on_hand')   AS DECIMAL(18,4))       AS on_hand,
    try_cast(json_extract_string(inv, '$.available') AS DECIMAL(18,4))       AS available,
    try_cast(json_extract_string(inv, '$.committed') AS DECIMAL(18,4))       AS committed,
    try_cast(json_extract_string(inv, '$.incoming')  AS DECIMAL(18,4))       AS incoming,
    try_cast(json_extract_string(inv, '$.onway')     AS DECIMAL(18,4))       AS onway,

    -- Reorder thresholds
    try_cast(json_extract_string(inv, '$.min_value') AS DECIMAL(18,4))       AS min_value,
    try_cast(json_extract_string(inv, '$.max_value') AS DECIMAL(18,4))       AS max_value,

    -- Moving average cost (source-provided)
    try_cast(json_extract_string(inv, '$.mac')       AS DECIMAL(18,4))       AS mac,

    -- Operational
    json_extract_string(inv, '$.bin_location')                               AS bin_location,
    try_cast(json_extract_string(inv, '$.wait_to_pack') AS DECIMAL(18,4))    AS wait_to_pack,

    -- Capture
    captured_at,
    capture_run_id

FROM inventories

{{ config(
    materialized='view',
    tags=['standard', 'inventory', 'history']
) }}

-- =================================================================================================
-- STANDARD: INVENTORY POSITION CAPTURES
-- =================================================================================================
-- Thin pass-through over stg_sapo_v2_inventory_position_captures.
-- Grain: one row per (capture run, variant_id, location_id): the stock position the source reported
-- at captured_at.
-- =================================================================================================

SELECT
    variant_id,
    product_id,
    sku,
    location_id,
    on_hand,
    available,
    committed,
    incoming,
    onway,
    min_value,
    max_value,
    mac,
    bin_location,
    wait_to_pack,
    captured_at,
    capture_run_id,
    'sapo_v2' AS source_system,
    'v2'      AS source_version
FROM {{ ref('stg_sapo_v2_inventory_position_captures') }}

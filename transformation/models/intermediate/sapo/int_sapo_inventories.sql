{{ config(
    tags=['int', 'sapo', 'inventory'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INTERMEDIATE: SAPO INVENTORIES (enriched + location-denormalized)
-- =================================================================================================
-- Purpose:
--   Flatten inventories_json from stg_sapo_variants into one row per
--   (variant_id, location_id), enrich with full inventory fields and
--   denormalized location name from dim_branch_location.
--
-- Source: stg_sapo_inventories (view — always latest snapshot per product_id)
-- Additional fields vs stg_sapo_inventories:
--   wait_to_pack, min_value, max_value (reparse from stg_sapo_variants.inventories_json)
--   location_name, location_code (from dim_branch_location)
--
-- CAVEAT: modified_on in Sapo inventory rows is always NULL — no intra-day history.
--   snapshot_date is derived from source_timestamp (= batch run event_timestamp).
-- =================================================================================================

WITH source AS (
    SELECT
        variant_id,
        product_id,
        sku,
        inventories_json,
        source_timestamp
    FROM {{ ref('stg_sapo_variants') }}
    WHERE inventories_json IS NOT NULL
      AND inventories_json NOT IN ('[]', 'null', '')
),

unnested AS (
    SELECT
        variant_id,
        product_id,
        sku,
        source_timestamp,
        unnest(from_json(inventories_json, '["JSON"]')) AS inv
    FROM source
),

inventory_fields AS (
    SELECT
        variant_id,
        product_id,
        sku,
        source_timestamp,

        -- Location key (VARCHAR — Sapo returns as string in JSON)
        json_extract_string(inv, '$.location_id')                                   AS location_id,

        -- Stock levels
        try_cast(json_extract_string(inv, '$.on_hand')   AS DECIMAL(18,4))          AS on_hand,
        try_cast(json_extract_string(inv, '$.available') AS DECIMAL(18,4))          AS available,
        try_cast(json_extract_string(inv, '$.committed') AS DECIMAL(18,4))          AS committed,
        try_cast(json_extract_string(inv, '$.incoming')  AS DECIMAL(18,4))          AS incoming,
        try_cast(json_extract_string(inv, '$.onway')     AS DECIMAL(18,4))          AS onway,

        -- Reorder thresholds (Sapo allows per-location min/max)
        try_cast(json_extract_string(inv, '$.min_value') AS DECIMAL(18,4))          AS min_value,
        try_cast(json_extract_string(inv, '$.max_value') AS DECIMAL(18,4))          AS max_value,

        -- Moving Average Cost
        try_cast(json_extract_string(inv, '$.mac')       AS DECIMAL(18,4))          AS mac,

        -- Operational
        json_extract_string(inv, '$.bin_location')                                  AS bin_location,
        try_cast(json_extract_string(inv, '$.wait_to_pack') AS DECIMAL(18,4))       AS wait_to_pack,

        -- Source timestamp metadata (always NULL from Sapo — snapshot only)
        try_cast(json_extract_string(inv, '$.modified_on') AS TIMESTAMPTZ)          AS inventory_modified_at

    FROM unnested
),

locations AS (
    SELECT
        CAST(branch_location_id AS VARCHAR)   AS location_id,
        branch_location_name,
        branch_location_code
    FROM {{ ref('dim_branch_location') }}
    WHERE branch_location_id IS NOT NULL
)

SELECT
    -- Identity
    inv.variant_id,
    inv.product_id,
    inv.sku,

    -- Location (denormalized for downstream convenience)
    inv.location_id,
    COALESCE(loc.branch_location_name, 'Unknown')   AS location_name,
    COALESCE(loc.branch_location_code, 'UNK')        AS location_code,

    -- Stock levels
    inv.on_hand,
    inv.available,
    inv.committed,
    inv.incoming,
    inv.onway,

    -- Thresholds
    inv.min_value,
    inv.max_value,

    -- Cost
    inv.mac,

    -- Operational
    inv.bin_location,
    inv.wait_to_pack,

    -- Metadata
    inv.inventory_modified_at,
    inv.source_timestamp,

    -- Snapshot date: date the batch captured this inventory state
    CAST(inv.source_timestamp AS DATE)               AS snapshot_date

FROM inventory_fields inv
LEFT JOIN locations loc
    ON inv.location_id = loc.location_id

{{ config(
    materialized='view',
    tags=['standard', 'products', 'prices']
) }}

-- =================================================================================================
-- HOP: STANDARD VARIANT PRICES - v2.0
-- =================================================================================================
-- Thin pass-through over stg_sapo_variant_prices.
-- Grain: 1 row per (variant_id × price_list_id).
-- Adds source lineage columns (source_system, source_version).
-- No column renames — faithful to stg output (P0 gate; renames are Phase 1+).
--
-- STD CONTRACT v2 (2026-06-03)
-- Interface for v3: stg_sapo_v3_variant_prices must produce:
--   variant_id (VARCHAR), product_id (VARCHAR), sku (VARCHAR),
--   price_list_id (VARCHAR), price_list_name (VARCHAR), price_list_code (VARCHAR),
--   is_cost_price (BOOLEAN), price_value (DECIMAL(18,2)), price_incl_tax (DECIMAL(18,2)),
--   source_timestamp (TIMESTAMPTZ)
-- Plus: source_system='sapo_v2', source_version='v2' (or 'v3' for v3 union)
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_variant_prices') }}
)

SELECT
    -- Keys
    variant_id,
    product_id,
    sku,

    -- Price list identification
    price_list_id,
    price_list_name,
    price_list_code,
    is_cost_price,

    -- Price values
    price_value,
    price_incl_tax,

    -- Metadata
    source_timestamp,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo_v2' AS source_system,
    'v2'   AS source_version

FROM source_data

{{ config(
    materialized='view',
    tags=['standard', 'products', 'variants']
) }}

-- =================================================================================================
-- HOP: STANDARD VARIANTS - v2.0
-- =================================================================================================
-- Thin pass-through over stg_sapo_variants.
-- Grain: 1 row per variant_id.
-- Adds source lineage columns (source_system, source_version).
-- No column renames — faithful to stg output (P0 gate; renames are Phase 1+).
--
-- CRITICAL: inventories_json is preserved for int_sapo_inventories, which re-unnests it.
--           variant_prices_json and composite_items_json also passed through for completeness.
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_variants') }}
)

SELECT
    -- Keys
    variant_id,
    product_id,
    sku,
    barcode,

    -- Names
    variant_name,
    product_name,

    -- Options
    opt1_value,
    opt2_value,
    opt3_value,

    -- Status
    variant_status,
    is_sellable,
    is_composite,

    -- Prices
    retail_price,
    wholesale_price,
    import_price,
    init_price,

    -- Unit
    unit,

    -- Weight
    weight_value,
    weight_unit,

    -- Tax
    is_taxable,
    is_tax_included,
    input_vat_rate,
    output_vat_rate,

    -- Pack size
    is_packsize,
    packsize_quantity,
    packsize_root_id,
    packsize_root_sku,

    -- Product type
    product_type,

    -- Timestamps
    created_at,
    modified_at,

    -- Nested JSON for further unnest (CRITICAL — consumers re-unnest these)
    variant_prices_json,
    inventories_json,       -- CRITICAL: int_sapo_inventories reads and re-unnests this
    composite_items_json,

    -- Metadata
    source_timestamp,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo' AS source_system,
    'v2'   AS source_version

FROM source_data

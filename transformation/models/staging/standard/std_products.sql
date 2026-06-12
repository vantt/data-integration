{{ config(
    materialized='view',
    tags=['standard', 'products']
) }}

-- STD CONTRACT v2 (2026-06-03) — interface for v3 stg_sapo_v3_products:
--   product_id (BIGINT), tenant_id (BIGINT),
--   product_name (VARCHAR), product_status (VARCHAR), product_type (VARCHAR), description (VARCHAR),
--   brand_id (BIGINT), brand (VARCHAR),
--   category_id (BIGINT), category (VARCHAR), category_code (VARCHAR),
--   opt1 (VARCHAR), opt2 (VARCHAR), opt3 (VARCHAR),
--   is_medicine (BOOLEAN), tags (VARCHAR),
--   image_path (VARCHAR), image_name (VARCHAR),
--   created_at (TIMESTAMPTZ), modified_at (TIMESTAMPTZ),
--   variants_json (JSON), options_json (JSON), images_json (JSON),
--   source_timestamp (TIMESTAMPTZ)
-- Plus: source_system='sapo', source_version IN ('v2','v3').

-- =================================================================================================
-- HOP: STANDARD PRODUCTS - v2.0
-- =================================================================================================
-- Thin pass-through over stg_sapo_products.
-- Grain: 1 row per product_id.
-- Adds source lineage columns (source_system, source_version).
-- No column renames — faithful to stg output (P0 gate; renames are Phase 1+).
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_products') }}
)

SELECT
    -- Keys
    product_id,
    tenant_id,

    -- Names / Status
    product_name,
    product_status,
    product_type,
    description,

    -- Brand
    brand_id,
    brand,

    -- Category
    category_id,
    category,
    category_code,

    -- Options (variant dimension names)
    opt1,
    opt2,
    opt3,

    -- Flags
    is_medicine,
    tags,

    -- Images
    image_path,
    image_name,

    -- Timestamps (TIMESTAMPTZ)
    created_at,
    modified_at,

    -- Nested JSON for downstream models
    variants_json,
    options_json,
    images_json,

    -- Metadata
    source_timestamp,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo' AS source_system,
    'v2'   AS source_version

FROM source_data

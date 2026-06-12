{{ config(
    materialized='view',
    tags=['staging', 'products']
) }}

-- =================================================================================================
-- STAGING: SAPO PRODUCTS
-- =================================================================================================
-- Purpose:
--   Clean product-level attributes from src_sapo_products.
--   Normalize unit casing, map product_type, standardize timestamps.
-- =================================================================================================

SELECT
    product_id,
    tenant_id,
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

    -- Options (variant dimension names, e.g. "Kích thước")
    opt1,
    opt2,
    opt3,

    -- Flags
    CASE WHEN medicine = 'true' THEN true ELSE false END as is_medicine,
    tags,

    -- Images
    image_path,
    image_name,

    -- Timestamps (TIMESTAMPTZ)
    try_cast(created_on AS TIMESTAMPTZ) as created_at,
    try_cast(modified_on AS TIMESTAMPTZ) as modified_at,

    -- Nested JSON for downstream models
    variants_json,
    options_json,
    images_json,

    -- Metadata
    event_timestamp as source_timestamp

FROM {{ ref('src_sapo_v2_products') }}

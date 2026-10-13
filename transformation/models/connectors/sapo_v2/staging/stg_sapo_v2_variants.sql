{{ config(
    materialized='view',
    tags=['staging', 'products', 'variants']
) }}

-- =================================================================================================
-- STAGING: SAPO VARIANTS
-- =================================================================================================
-- Purpose:
--   Unnest variants_json from src_sapo_products into one row per variant.
--   Extracts scalar fields, normalizes unit casing, casts price/weight columns.
--   variant_prices and inventories kept as JSON for further unnest if needed.
-- =================================================================================================

WITH source AS (
    SELECT * FROM {{ ref('src_sapo_v2_products') }}
),

unnested AS (
    SELECT
        product_id,
        event_timestamp,
        unnest(from_json(variants_json, '["JSON"]')) as v
    FROM source
    WHERE variants_json IS NOT NULL
      AND variants_json NOT IN ('[]', 'null', '')
)

SELECT
    -- Keys
    json_extract_string(v, '$.id') as variant_id,
    product_id,
    json_extract_string(v, '$.sku') as sku,
    json_extract_string(v, '$.barcode') as barcode,

    -- Names
    json_extract_string(v, '$.name') as variant_name,
    json_extract_string(v, '$.product_name') as product_name,

    -- Options (variant option values, e.g. "Mặc định", "60 viên")
    json_extract_string(v, '$.opt1') as opt1_value,
    json_extract_string(v, '$.opt2') as opt2_value,
    json_extract_string(v, '$.opt3') as opt3_value,

    -- Status
    json_extract_string(v, '$.status') as variant_status,
    CASE WHEN json_extract_string(v, '$.sellable') = 'true' THEN true ELSE false END as is_sellable,
    CASE WHEN json_extract_string(v, '$.composite') = 'true' THEN true ELSE false END as is_composite,

    -- Prices
    try_cast(json_extract_string(v, '$.variant_retail_price') as DECIMAL(18,2)) as retail_price,
    try_cast(json_extract_string(v, '$.variant_whole_price') as DECIMAL(18,2)) as wholesale_price,
    try_cast(json_extract_string(v, '$.variant_import_price') as DECIMAL(18,2)) as import_price,
    try_cast(json_extract_string(v, '$.init_price') as DECIMAL(18,2)) as init_price,

    -- Unit (normalize: capitalize first letter)
    CASE
        WHEN json_extract_string(v, '$.unit') IS NULL THEN NULL
        ELSE upper(left(json_extract_string(v, '$.unit'), 1))
             || substr(json_extract_string(v, '$.unit'), 2)
    END as unit,

    -- Weight
    try_cast(json_extract_string(v, '$.weight_value') as DECIMAL(12,2)) as weight_value,
    json_extract_string(v, '$.weight_unit') as weight_unit,

    -- Tax
    CASE WHEN json_extract_string(v, '$.taxable') = 'true' THEN true ELSE false END as is_taxable,
    CASE WHEN json_extract_string(v, '$.tax_included') = 'true' THEN true ELSE false END as is_tax_included,
    try_cast(json_extract_string(v, '$.input_vat_rate') as DECIMAL(5,2)) as input_vat_rate,
    try_cast(json_extract_string(v, '$.output_vat_rate') as DECIMAL(5,2)) as output_vat_rate,

    -- Pack size
    CASE WHEN json_extract_string(v, '$.packsize') = 'true' THEN true ELSE false END as is_packsize,
    json_extract_string(v, '$.packsize_quantity') as packsize_quantity,
    json_extract_string(v, '$.packsize_root_id') as packsize_root_id,
    json_extract_string(v, '$.packsize_root_sku') as packsize_root_sku,

    -- Product type (from variant level)
    json_extract_string(v, '$.product_type') as product_type,

    -- Timestamps
    try_cast(json_extract_string(v, '$.created_on') AS TIMESTAMPTZ) as created_at,
    try_cast(json_extract_string(v, '$.modified_on') AS TIMESTAMPTZ) as modified_at,

    -- Nested JSON for further unnest
    json_extract_string(v, '$.variant_prices') as variant_prices_json,
    json_extract_string(v, '$.inventories') as inventories_json,
    json_extract_string(v, '$.composite_items') as composite_items_json,

    -- Metadata
    event_timestamp as source_timestamp

FROM unnested

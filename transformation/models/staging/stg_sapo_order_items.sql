{{ config(
    materialized='view',
    tags=['staging', 'orders', 'items']
) }}

-- =================================================================================================
-- STAGING: SAPO ORDER ITEMS
-- =================================================================================================
-- Purpose:
--   Unnest order_line_items_json from src_sapo_orders into one row per line item.
-- =================================================================================================

WITH raw_source AS (
    SELECT * FROM {{ ref('src_sapo_orders') }}
),

unnested_items AS (
    SELECT
        entity_id as order_entity_id,
        order_id,
        order_code,
        event_timestamp,
        unnest(from_json(order_line_items_json, '["JSON"]')) as item_json
    FROM raw_source
    WHERE order_line_items_json IS NOT NULL
)

SELECT
    order_id,
    order_code,

    -- Item Details
    json_extract_string(item_json, '$.id') as item_id,
    json_extract_string(item_json, '$.product_id') as product_id,
    json_extract_string(item_json, '$.variant_id') as variant_id,
    json_extract_string(item_json, '$.sku') as sku,
    json_extract_string(item_json, '$.product_name') as product_name,
    json_extract_string(item_json, '$.variant_name') as variant_name,

    try_cast(json_extract_string(item_json, '$.quantity') as DECIMAL(18,2)) as quantity,
    try_cast(json_extract_string(item_json, '$.price') as DECIMAL(18,2)) as unit_price,
    try_cast(json_extract_string(item_json, '$.line_amount') as DECIMAL(18,2)) as line_amount,

    try_cast(json_extract_string(item_json, '$.discount_amount') as DECIMAL(18,2)) as discount_amount,
    try_cast(json_extract_string(item_json, '$.distributed_discount_amount') as DECIMAL(18,2)) as distributed_discount_amount,
    json_extract_string(item_json, '$.lots_dates') as lots_dates,

    json_extract_string(item_json, '$.grams') as weight,
    json_extract_string(item_json, '$.vendor') as vendor,
    json_extract_string(item_json, '$.product_type') as product_type,
    json_extract_string(item_json, '$.barcode') as barcode,
    json_extract_string(item_json, '$.unit') as unit,

    event_timestamp as source_timestamp

FROM unnested_items

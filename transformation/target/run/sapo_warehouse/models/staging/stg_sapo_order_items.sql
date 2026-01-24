
  
  create view "data_integration2"."main_staging"."stg_sapo_order_items__dbt_tmp" as (
    

-- =================================================================================================
-- HOP 5: STAGING - SAPO ORDER ITEMS
-- =================================================================================================
-- Purpose:
-- 1. Unnest the `order_line_items` array from the Sapo Order JSON payload.
-- 2. Create a granular table with one row per line item.
--
-- Logic:
-- - Uses `unnest(from_json(...))` to explode the JSON array.
-- - Extracts product details: SKU, Name, Variant, Price, Quantity.
-- - Calculates `total_price` (check regular logic: quantity * price).
-- =================================================================================================

WITH raw_source AS (
    SELECT * FROM "data_integration2"."main_staging"."src_sapo_orders"
),

unnested_items AS (
    SELECT
        entity_id as order_entity_id,
        json_extract_string(payload, '$.id') as order_id,
        json_extract_string(payload, '$.code') as order_code,
        json_extract_string(payload, '$.id') as order_id,
        json_extract_string(payload, '$.code') as order_code,
        event_timestamp,
        
        -- UNNEST the items array
        -- DuckDB: unnest(json_extract_string(payload, '$.order_line_items')::JSON[]) 
        -- Note: strict JSON path syntax might differ, using list extraction
        unnest(from_json(json_extract_string(payload, '$.order_line_items'), '["JSON"]')) as item_json
        
    FROM raw_source
    WHERE json_extract_string(payload, '$.order_line_items') IS NOT NULL
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
    try_cast(json_extract_string(item_json, '$.line_amount') as DECIMAL(18,2)) as total_price,
    
    json_extract_string(item_json, '$.grams') as weight,
    json_extract_string(item_json, '$.vendor') as vendor,
    json_extract_string(item_json, '$.product_type') as product_type,
    
    json_extract_string(item_json, '$.product_type') as product_type,
    
    event_timestamp as source_timestamp

FROM unnested_items
  );

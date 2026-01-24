{{ config(
    materialized='view',
    tags=['standard', 'items']
) }}

-- =================================================================================================
-- HOP 5: STANDARD ORDER ITEMS - v2.0
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_order_items') }}
)

SELECT
    -- IDs
    item_id,
    order_id,
    product_id,
    variant_id,
    
    -- Product Info
    sku,
    -- barcode, -- Add if available in staging later
    product_name,
    variant_name,
    
    -- Quantity & Price
    quantity,
    unit_price,
    total_price,
    
    -- Enriched Attributes (v2)
    try_cast(weight as DECIMAL(18,2)) as weight_grams,
    
    -- Standard Fields
    -- MRP Price, Discount Amount could be calculated here if raw data supports it.
    product_type,
    
    source_timestamp as extracted_at

FROM source_data

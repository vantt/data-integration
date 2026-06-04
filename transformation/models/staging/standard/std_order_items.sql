{{ config(
    materialized='view',
    tags=['standard', 'items']
) }}

-- =================================================================================================
-- HOP 5: STANDARD ORDER ITEMS - v2.0
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_order_items_v2') }}
)

SELECT
    -- IDs
    item_id AS order_line_id,
    order_id,
    product_id,
    variant_id,
    
    -- Product Info
    sku,
    barcode,
    unit,
    product_name,
    variant_name,
    
    -- Quantity & Price
    quantity,
    unit_price,
    line_amount,
    
    discount_amount,
    distributed_discount_amount,
    lots_dates,
    
    -- Enriched Attributes (v2)
    try_cast(weight as DECIMAL(18,2)) as weight_grams,
    
    vendor,

    -- Standard Fields
    -- MRP Price, Discount Amount could be calculated here if raw data supports it.
    product_type,
    
    source_timestamp as extracted_at,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo' as source_system,
    'v2'   as source_version

FROM source_data

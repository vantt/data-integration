{{ config(
    materialized='view',
    tags=['standard', 'items']
) }}

-- =================================================================================================
-- HOP 5: STANDARD ORDER ITEMS - v2.0
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_order_items') }}
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
    (line_amount = 0) AS is_gift_line,

    discount_amount,
    distributed_discount_amount,
    -- Rate: discount_amount / gross_line_amount (unit_price × quantity = pre-discount price)
    -- NULL when no discount or price is zero (avoid division by zero)
    CASE
        WHEN discount_amount > 0 AND unit_price > 0 AND quantity > 0
        THEN ROUND(
            discount_amount / NULLIF(unit_price * quantity, 0),
            4  -- keep 4 decimal places (~0.01% precision)
        )
        ELSE NULL
    END AS discount_rate,
    lots_dates,
    
    -- Enriched Attributes (v2)
    try_cast(weight as DECIMAL(18,2)) as weight_grams,
    
    vendor,

    -- Standard Fields
    -- MRP Price, Discount Amount could be calculated here if raw data supports it.
    product_type,
    
    source_timestamp as extracted_at,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo_v2' as source_system,
    'v2'   as source_version

FROM source_data

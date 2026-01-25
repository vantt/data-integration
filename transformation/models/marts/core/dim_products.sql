{{ config(
    tags=['mart', 'dim'],
    materialized='incremental',
    unique_key='product_key'
) }}

WITH order_items AS (
    SELECT * FROM {{ ref('std_order_items') }}
    {% if is_incremental() %}
    -- Only process items extracted since the last run
    WHERE extracted_at > (SELECT MAX(last_seen_at) FROM {{ this }})
    {% endif %}
),

ranked_products AS (
    -- Strategy: "Last Record Wins"
    -- Since we don't have a dedicated Product Sync yet, we extract products from Order Items.
    -- We use ROW_NUMBER() ordered by extracted_at DESC to always get the LATEST version of the product 
    -- (e.g., if name or price changed, we get the new one).
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY product_id, variant_id 
            ORDER BY extracted_at DESC
        ) as rn
    FROM order_items
    WHERE product_id IS NOT NULL 
)

SELECT
    -- Surrogate Key
    md5(product_id || '-' || coalesce(variant_id, '')) as product_key,
    
    -- Natural Keys
    product_id,
    variant_id,
    sku,
    barcode,
    
    -- Attributes (Last Wins)
    product_name,
    variant_name,
    product_type,
    unit,
    weight_grams,
    unit_price as last_sold_price,
    
    -- Metadata
    extracted_at as last_seen_at

FROM ranked_products
WHERE rn = 1

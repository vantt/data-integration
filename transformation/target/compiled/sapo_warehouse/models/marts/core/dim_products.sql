

WITH order_items AS (
    SELECT * FROM "data_integration2"."main_staging"."std_order_items"
),

ranked_products AS (
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
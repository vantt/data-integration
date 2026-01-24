

WITH order_items AS (
    SELECT * FROM "data_integration2"."main_staging"."std_order_items"
)

SELECT
    -- Surrogate Key
    md5(product_id || '-' || variant_id) as product_key,
    
    -- Natural Keys
    product_id,
    variant_id,
    MAX(sku) as sku,
    
    -- Attributes (Use max to pick one value if duplicates exist)
    MAX(product_name) as product_name,
    MAX(variant_name) as variant_name,
    MAX(weight_grams) as weight_grams
    
FROM order_items
WHERE product_id IS NOT NULL AND variant_id IS NOT NULL
GROUP BY product_id, variant_id
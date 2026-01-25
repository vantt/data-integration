{{ config(
    tags=['mart', 'dim']
) }}

WITH items AS (
    SELECT * FROM {{ ref('std_order_items') }}
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(["coalesce(product_type, 'Unknown')"]) }} as category_key,
    
    -- Business Key
    coalesce(product_type, 'Unknown') as category_name,
    product_type,
    
    -- Hierarchy placeholders (can be enriched later)
    cast(null as string) as parent_category_name,
    cast(1 as int) as category_level

FROM items
WHERE product_type IS NOT NULL OR product_type IS NULL

{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH items AS (
    SELECT * FROM {{ ref('std_order_items') }}
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(["coalesce(product_type, 'Unknown')"]) }} as product_type_key,
    
    -- Business Key
    coalesce(product_type, 'Unknown') as product_type_name,
    product_type

FROM items
WHERE product_type IS NOT NULL OR product_type IS NULL

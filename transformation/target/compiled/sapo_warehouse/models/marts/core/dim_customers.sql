

WITH customers AS (
    SELECT * FROM "data_integration2"."main_staging"."std_customers"
)

SELECT
    -- Surrogate Key (using md5 for stability)
    md5(customer_id) as customer_key,
    
    -- Natural Keys
    customer_id,
    
    -- Attributes
    full_name,
    email,
    phone,
    
    -- Address
    city,
    province,
    district,
    ward,
    address1,
    country,
    
    -- We can categorize customers based on spending here if needed
    CASE 
        WHEN total_spent > 10000000 THEN 'VIP'
        WHEN total_spent > 5000000 THEN 'Loyal'
        ELSE 'Regular'
    END as customer_segment,
    
    total_spent as lifetime_value,
    total_orders_count,
    
    created_at,
    updated_at

FROM customers

UNION ALL

SELECT
    md5('Unknown') as customer_key,
    'Unknown' as customer_id,
    'Unknown' as full_name,
    'Unknown' as email,
    'Unknown' as phone,
    'Unknown' as city,
    'Unknown' as province,
    'Unknown' as district,
    'Unknown' as ward,
    'Unknown' as address1,
    'Unknown' as country,
    'Unknown' as customer_segment,
    0 as lifetime_value,
    0 as total_orders_count,
    NULL as created_at,
    NULL as updated_at
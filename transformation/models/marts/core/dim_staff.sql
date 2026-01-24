{{ config(
    tags=['mart', 'dim']
) }}

WITH orders AS (
    SELECT * FROM {{ ref('std_orders') }}
)

SELECT DISTINCT
    -- Surrogate Key
    md5(salesperson_id) as staff_key,
    
    salesperson_id as staff_id,
    
    -- Placeholder for name until we have a proper HR source
    'Staff ' || salesperson_id as full_name,
    cast(null as string) as email

FROM orders
WHERE salesperson_id IS NOT NULL

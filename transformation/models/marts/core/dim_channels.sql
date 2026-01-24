{{ config(
    tags=['mart', 'dim']
) }}

WITH orders AS (
    SELECT * FROM {{ ref('std_orders') }}
)

SELECT DISTINCT
    -- Surrogate Key
    md5(channel) as channel_key,
    
    channel as channel_name,
    channel as channel_code, -- Placeholder
    'Sales Channel' as channel_type -- Placeholder

FROM orders
WHERE channel IS NOT NULL

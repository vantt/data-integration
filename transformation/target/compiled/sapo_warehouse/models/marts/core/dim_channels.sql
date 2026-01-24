

WITH orders AS (
    SELECT * FROM "data_integration2"."main_staging"."std_orders"
)

SELECT DISTINCT
    -- Surrogate Key
    md5(channel) as channel_key,
    
    channel as channel_name,
    channel as channel_code, -- Placeholder
    'Sales Channel' as channel_type -- Placeholder

FROM orders
WHERE channel IS NOT NULL
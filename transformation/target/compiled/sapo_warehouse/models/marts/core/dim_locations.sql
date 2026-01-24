

WITH orders AS (
    SELECT * FROM "data_integration2"."main_staging"."std_orders"
)

SELECT DISTINCT
    -- Surrogate Key
    md5(location_id) as location_key,
    
    location_id
    -- join with ref_locations if available for name
    -- otherwise just expose ID for now

FROM orders
WHERE location_id IS NOT NULL
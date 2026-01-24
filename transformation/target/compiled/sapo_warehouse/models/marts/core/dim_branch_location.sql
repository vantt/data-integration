

WITH locations AS (
    SELECT * FROM "data_integration2"."main"."ref_locations"
)

SELECT DISTINCT
    -- Surrogate Key
    md5(cast(id as string)) as branch_location_key,
    
    cast(id as integer) as branch_location_id,
    name as branch_location_name,
    code as branch_location_code

FROM locations
WHERE id IS NOT NULL
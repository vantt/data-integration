{{ config(
    tags=['mart', 'dim']
) }}

WITH locations AS (
    SELECT * FROM {{ ref('ref_locations') }}
)

SELECT DISTINCT
    -- Surrogate Key
    md5(cast(id as string)) as branch_location_key,
    
    cast(id as integer) as branch_location_id,
    name as branch_location_name,
    code as branch_location_code

FROM locations
WHERE id IS NOT NULL

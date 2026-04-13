{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH locations AS (
    SELECT * FROM {{ ref('ref_branch_locations') }}
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['cast(id as string)']) }} as branch_location_key,
    
    cast(id as integer) as branch_location_id,
    name as branch_location_name,
    code as branch_location_code

FROM locations
WHERE id IS NOT NULL

UNION ALL

-- Unknown Member
SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as branch_location_key,
    cast(null as integer) as branch_location_id,
    'Unknown' as branch_location_name,
    'UNK' as branch_location_code

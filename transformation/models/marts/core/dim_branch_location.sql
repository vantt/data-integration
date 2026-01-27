{{ config(
    tags=['mart', 'dim'],
    location="{{ env_var('DBT_EXPORT_PATH') }}/{{ this.name }}/{{ this.name }}_{{ run_started_at.strftime('%Y%m%d%H%M%S') }}.parquet"
) }}

WITH locations AS (
    SELECT * FROM {{ ref('ref_locations') }}
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['cast(id as string)']) }} as branch_location_key,
    
    cast(id as integer) as branch_location_id,
    name as branch_location_name,
    code as branch_location_code

FROM locations
WHERE id IS NOT NULL

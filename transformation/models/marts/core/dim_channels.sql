{{ config(
    tags=['mart', 'dim'],
    location="{{ env_var('DBT_EXPORT_PATH') }}/{{ this.name }}/{{ this.name }}_{{ run_started_at.strftime('%Y%m%d%H%M%S') }}.parquet"
) }}

WITH orders AS (
    SELECT * FROM {{ ref('std_orders') }}
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['channel']) }} as channel_key,
    
    channel as channel_name,
    channel as channel_code, -- Placeholder
    'Sales Channel' as channel_type -- Placeholder

FROM orders
WHERE channel IS NOT NULL

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as channel_key,
    'Unknown' as channel_name,
    'Unknown' as channel_code,
    'Unknown' as channel_type

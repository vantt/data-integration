{{ config(
    tags=['mart', 'dim'],
    location="{{ env_var('DBT_EXPORT_PATH') }}/{{ this.name }}/{{ this.name }}_{{ run_started_at.strftime('%Y%m%d%H%M%S') }}.parquet"
) }}

-- Static dimension for status analysis
-- Static dimension for status analysis
SELECT {{ dbt_utils.generate_surrogate_key(["'OPEN'"]) }} as status_key, 'OPEN' as status_code, 'Open Orders' as description
UNION ALL SELECT {{ dbt_utils.generate_surrogate_key(["'COMPLETED'"]) }}, 'COMPLETED', 'Completed Orders'
UNION ALL SELECT {{ dbt_utils.generate_surrogate_key(["'CANCELLED'"]) }}, 'CANCELLED', 'Cancelled Orders'
UNION ALL SELECT {{ dbt_utils.generate_surrogate_key(["'ARCHIVED'"]) }}, 'ARCHIVED', 'Archived Orders'
UNION ALL SELECT {{ dbt_utils.generate_surrogate_key(["'DRAFT'"]) }}, 'DRAFT', 'Draft Orders'

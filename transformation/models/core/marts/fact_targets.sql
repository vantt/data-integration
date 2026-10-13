{{ config(

    tags=['mart', 'core', 'targets'],
    location="{{ get_rolling_location() }}"
) }}

WITH staged AS (
    SELECT * FROM {{ ref('stg_targets') }}
),

dim_date AS (
    SELECT date_key, date_actual FROM {{ ref('dim_date') }}
),

dim_branch AS (
    SELECT branch_location_key, branch_location_code FROM {{ ref('dim_branch_location') }}
),

dim_staff AS (
    SELECT staff_key, email FROM {{ ref('dim_staff') }}
),

dim_channel AS (
    SELECT channel_key, channel_name FROM {{ ref('dim_channels') }}
),

dim_product AS (
    SELECT product_key, sku FROM {{ ref('dim_products') }}
)

SELECT
    s.target_key,
    s.target_code,

    -- Cycle
    d.date_key,
    s.cycle_start_date as target_date,
    s.cycle_start_date,
    s.cycle_end_date,
    s.cycle_type,

    -- Organization Dimensions (Left Join to preserve targets even if dimension is missing)
    coalesce(b.branch_location_key, {{ dbt_utils.generate_surrogate_key(["'-1'"]) }}) as branch_key,
    coalesce(st.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as staff_key,

    -- Other Dimensions
    coalesce(c.channel_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as channel_key,
    coalesce(p.product_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as product_key,

    -- Team (Currently just raw code, pending Dimension)
    s.team_code,

    -- Scope fields (raw values for flexible matching)
    s.branch_code as scope_branch,
    s.staff_email as scope_staff,
    s.sales_channel as scope_channel,
    s.product_sku as scope_product,

    -- Metrics
    s.metric_code,
    s.target_val,

    -- Metadata
    s.description,
    current_timestamp as loaded_at

FROM staged s
LEFT JOIN dim_date d ON s.cycle_start_date = d.date_actual
LEFT JOIN dim_branch b ON s.branch_code = b.branch_location_code
LEFT JOIN dim_staff st ON s.staff_email = st.email
LEFT JOIN dim_channel c ON s.sales_channel = c.channel_name
LEFT JOIN dim_product p ON s.product_sku = p.sku

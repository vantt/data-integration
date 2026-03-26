{{ config(
    materialized='view',
    tags=['staging', 'targets']
) }}

WITH raw_targets AS (
    SELECT * FROM {{ source('sapo_raw', 'targets_raw') }}
),

sanitized AS (
    SELECT
        -- 1. Cycle: start date + type
        -- Column renamed from setup_date to cycle_start_date in the Sheet
        try_cast(
            coalesce(cycle_start_date, setup_date) as date
        ) as cycle_start_date,

        -- Cycle type: daily, weekly, monthly, quarterly, yearly
        -- Default to 'monthly' for backward compatibility with old rows
        coalesce(
            nullif(lower(trim(cast(cycle_type as string))), ''),
            'monthly'
        ) as cycle_type,

        -- 2. Scope Fields (empty = ALL = not constrained by that dimension)
        coalesce(nullif(trim(cast(branch_code as string)), ''), 'ALL') as branch_code,
        coalesce(nullif(trim(cast(team_code as string)), ''), 'ALL') as team_code,
        coalesce(nullif(trim(cast(staff_email as string)), ''), 'ALL') as staff_email,
        coalesce(nullif(trim(cast(sales_channel as string)), ''), 'ALL') as sales_channel,
        coalesce(nullif(trim(cast(product_sku as string)), ''), 'ALL') as product_sku,

        -- 3. Metric & Value
        lower(trim(cast(metric_code as string))) as metric_code,
        try_cast(target_value as decimal(18,2)) as target_val,

        -- 4. Metadata
        cast(description as string) as description,
        cast(ingest_method as string) as ingest_method,
        year,
        month

    FROM raw_targets
),

with_cycle_end AS (
    SELECT
        *,
        -- Derive cycle_end_date from cycle_start_date + cycle_type
        CASE cycle_type
            WHEN 'daily'     THEN cycle_start_date
            WHEN 'weekly'    THEN cycle_start_date + INTERVAL '6 days'
            WHEN 'monthly'   THEN (cycle_start_date + INTERVAL '1 month' - INTERVAL '1 day')::date
            WHEN 'quarterly' THEN (cycle_start_date + INTERVAL '3 months' - INTERVAL '1 day')::date
            WHEN 'yearly'    THEN (cycle_start_date + INTERVAL '1 year' - INTERVAL '1 day')::date
            ELSE (cycle_start_date + INTERVAL '1 month' - INTERVAL '1 day')::date
        END as cycle_end_date
    FROM sanitized
),

generated_keys AS (
    SELECT
        *,
        -- Generate Semantic Code: TGT-{CycleStart}-{Branch}-{Team}-{Staff}-{Metric}
        concat_ws('-',
            'TGT',
            strftime(coalesce(cycle_start_date, '1900-01-01'::date), '%Y%m%d'),
            cycle_type,
            branch_code,
            team_code,
            staff_email,
            metric_code
        ) as target_code
    FROM with_cycle_end
)

SELECT
    -- Technical Primary Key
    {{ dbt_utils.generate_surrogate_key(['target_code']) }} as target_key,

    target_code,

    -- Cycle
    cycle_start_date,
    cycle_end_date,
    cycle_type,

    -- Scope
    branch_code,
    team_code,
    staff_email,
    sales_channel,
    product_sku,

    -- Metrics
    metric_code,
    target_val,

    -- Metadata
    description,
    ingest_method

FROM generated_keys
WHERE target_val IS NOT NULL

{{ config(
    materialized='view',
    tags=['staging', 'targets']
) }}

WITH raw_targets AS (
    SELECT * FROM {{ source('sapo_raw', 'targets_raw') }}
),

sanitized AS (
    SELECT
        -- 1. Setup Date -> Date Key
        try_cast(setup_date as date) as target_date,
        
        -- 2. Business Keys (Handle Empty as 'All')
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

generated_keys AS (
    SELECT
        *,
        -- Generate Semantic Code: TGT-{Month}-{Branch}-{Team}-{Staff}-{Metric}
        -- We hash this to create the surrogate key
        concat_ws('-', 
            'TGT',
            strftime(coalesce(target_date, '1900-01-01'::date), '%Y%m'),
            branch_code,
            team_code,
            staff_email,
            metric_code
        ) as target_code
    FROM sanitized
)

SELECT
    -- Technical Primary Key
    md5(target_code) as target_key,
    
    target_code,
    
    -- Dimensions
    target_date,
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

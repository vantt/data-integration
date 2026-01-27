{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'dim'],
    post_hook=[
      "COPY (SELECT * FROM {{ this }}) TO '{{ env_var('DBT_EXPORT_PATH') }}/dim_customers/dim_customers_{{ run_started_at.strftime('%Y%m%d%H%M%S') }}.parquet' (FORMAT PARQUET)"
    ]
) }}

WITH customers AS (
    SELECT * FROM {{ ref('dim_customers_base') }}
),

metrics AS (
    SELECT * FROM {{ ref('int_customer_metrics') }}
),

joined_data AS (
    SELECT
        c.customer_key,
        c.customer_id,
        c.full_name,
        c.email,
        c.phone,
        c.city,
        c.province,
        c.district,
        c.ward,
        c.address1,
        c.country,
        c.created_at,
        c.updated_at as source_updated_at,
        
        -- Metrics from intermediate model
        m.first_order_date,
        m.last_order_date,
        m.recency_days,
        m.frequency,
        m.monetary_value,
        m.lifespan_days,
        m.metric_calculated_at,

        -- [METRIC] Customer Status (RFM - Recency Component)
        -- Logic:
        -- - Active: Bought within the last 30 days.
        -- - At Risk: Bought between 31 and 90 days ago.
        -- - Churned: No purchase for over 90 days.
        CASE 
            WHEN m.recency_days <= 30 THEN 'Active'
            WHEN m.recency_days <= 90 THEN 'At Risk'
            WHEN m.recency_days > 90 THEN 'Churned'
            ELSE 'New/Unknown'
        END as customer_status,

        -- Calculate a combined updated timestamp for incremental loading
        GREATEST(c.updated_at, COALESCE(m.metric_calculated_at, c.updated_at)) as last_modified
        
    FROM customers c
    LEFT JOIN metrics m ON c.customer_key = m.customer_key
)

SELECT
    customer_key,
    customer_id,
    full_name,
    email,
    phone,
    city,
    province,
    district,
    ward,
    address1,
    country,
    
    -- [METRIC] Customer Segmentation (RFM - Monetary Component)
    -- Logic: Based on fixed thresholds of Lifetime Value (GMV).
    -- - VIP: > 10,000,000 VND
    -- - Loyal: 5,000,000 - 10,000,000 VND
    -- - Regular: < 5,000,000 VND
    CASE 
        WHEN monetary_value > 10000000 THEN 'VIP'
        WHEN monetary_value > 5000000 THEN 'Loyal'
        ELSE 'Regular'
    END as customer_segment,

    -- CLV & RFM
    COALESCE(monetary_value, 0) as lifetime_value,
    COALESCE(frequency, 0) as total_orders_count,
    first_order_date,
    last_order_date,
    recency_days,
    lifespan_days,
    customer_status,
    
    created_at,
    source_updated_at as updated_at,
    last_modified

FROM joined_data

{% if is_incremental() %}
WHERE last_modified >= (SELECT MAX(last_modified) FROM {{ this }})
{% endif %}

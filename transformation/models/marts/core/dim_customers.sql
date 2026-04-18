{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'dim'],
    post_hook=[
      "COPY (SELECT * FROM {{ this }}) TO '{{ get_rolling_location() }}' (FORMAT PARQUET)"
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
        c.dob,
        c.sex,
        c.customer_group,
        c.loyalty_point,
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
    
    -- value_group: Customer value tier based on lifetime spend
    -- See docs/context/customer-segmentation.md for definitions
    CASE
        WHEN monetary_value >= 50000000 OR frequency >= 20 THEN 'VALUE_VIP'
        WHEN monetary_value >= 20000000 THEN 'VALUE_GOLD'
        WHEN monetary_value >= 5000000 THEN 'VALUE_SILVER'
        ELSE 'VALUE_BRONZE'
    END as value_group,

    -- Demographics
    dob,
    sex,
    customer_group,
    loyalty_point,

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

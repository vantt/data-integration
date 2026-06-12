{{ config(
    materialized='view',
    tags=['standard', 'customers']
) }}

-- =================================================================================================
-- HOP 5: STANDARD CUSTOMERS
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_customers') }}
)

SELECT
    -- Identity
    sapo_customer_id as customer_id,
    customer_code,
    'sapo' as source_system,
    'v2'   as source_version,
    
    -- Contact
    full_name,
    email,
    phone_number as phone,

    -- Address
    city,
    province,
    district,
    ward,
    address1,
    country,
    
    -- Attributes
    dob AS birth_date,
    sex AS gender,
    customer_group,
    loyalty_point AS loyalty_points,

    -- Metrics
    coalesce(total_expense, 0) as total_spend,  -- P1 R1: customer SPEND (src $.total_expense; 'expense' = business cost, wrong term)
    coalesce(orders_count, 0) as order_count,
    debt,
    
    -- Timestamps
    try_cast(created_on as TIMESTAMPTZ) as created_at,
    try_cast(modified_on as TIMESTAMPTZ) as updated_at

FROM source_data

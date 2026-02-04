{{ config(
    materialized='view',
    tags=['standard', 'customers']
) }}

-- =================================================================================================
-- HOP 5: STANDARD CUSTOMERS
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_customers') }}
)

SELECT
    -- Identity
    sapo_customer_id as customer_id,
    'sapo' as source_system,
    
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
    dob,
    sex,
    customer_group,
    loyalty_point,

    -- Metrics
    coalesce(total_expense, 0) as total_expense,
    coalesce(orders_count, 0) as total_orders_count,
    debt,
    
    -- Timestamps
    try_cast(created_on as TIMESTAMP) as created_at,
    try_cast(modified_on as TIMESTAMP) as updated_at

FROM source_data

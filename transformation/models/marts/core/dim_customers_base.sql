{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'dim', 'base']
) }}

WITH customers AS (
    SELECT * FROM {{ ref('std_customers') }}
)

SELECT
    -- Surrogate Key (using md5 for stability)
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_key,
    
    -- Natural Keys
    customer_id,
    
    -- Attributes
    full_name,
    email,
    phone,
    
    -- Address
    city,
    province,
    district,
    ward,
    address1,
    country,
    
    -- Timestamps
    created_at,
    updated_at

FROM customers

{% if is_incremental() %}
WHERE updated_at >= (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as customer_key,
    'Unknown' as customer_id,
    'Unknown' as full_name,
    'Unknown' as email,
    'Unknown' as phone,
    'Unknown' as city,
    'Unknown' as province,
    'Unknown' as district,
    'Unknown' as ward,
    'Unknown' as address1,
    'Unknown' as country,
    NULL as created_at,
    NULL as updated_at

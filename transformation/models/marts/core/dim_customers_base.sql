{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'dim', 'base']
) }}

/*
    ARCHITECTURAL NOTE: ROLE OF DIM_CUSTOMERS_BASE
    
    1. Single Source of Truth for Keys:
       This model generates the canonical `customer_key` (Surrogate Key) for the entire data warehouse.
       All downstream models (Facts, Dimensions) must reference this key to ensure consistency.

    2. Circular Dependency Breaker:
       - `fact_orders` needs a `customer_key` to link orders to customers.
       - `dim_customers` (the final Mart) needs `fact_orders` to calculate metrics (e.g., total spend, VIP status).
       - DIRECT LINK would cause: dim_customers -> fact_orders -> dim_customers (CIRCULAR ERROR).
       - SOLUTION:
            dim_customers_base (Keys & Profile) --> fact_orders
                                                      |
            dim_customers (Final) <-------------------+
       
    3. Not for Serving:
       This model is an internal building block. It is NOT exported to the Serving Layer (Metabase).
       End users should only use `dim_customers`, which includes all fields from Base + calculated Metrics.
*/

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
    
    dob,
    sex,
    customer_group,
    loyalty_point,
    
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
    NULL as dob,
    'Unknown' as sex,
    'Unknown' as customer_group,
    0 as loyalty_point,
    'Unknown' as city,
    'Unknown' as province,
    'Unknown' as district,
    'Unknown' as ward,
    'Unknown' as address1,
    'Unknown' as country,
    NULL as created_at,
    NULL as updated_at

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
    customer_code,

    -- Attributes
    full_name,
    email,
    phone,
    status,

    birth_date,
    gender,
    customer_group,  -- raw JSON blob, kept for reference; use the 3 columns below instead
    customer_group_id,
    customer_group_code,
    customer_group_name,
    loyalty_points,

    -- Address (primary address from addresses[0])
    city,
    province,
    district,
    ward,
    address1,
    country,
    address2,
    zip,
    company,
    address_phone,

    -- B2B / misc scalars
    assignee_id,
    tax_number,
    website,
    description,
    default_discount_rate,
    default_price_list_id,

    -- Financials
    debt,

    -- JSON text (for dim_customers passthrough to Metabase and CRM)
    loyalty_customer_json,
    social_customers_json,

    -- Timestamps
    created_at,
    updated_at

FROM customers

{% if is_incremental() %}
WHERE updated_at >= (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}

-- Unknown sentinel: always included outside the incremental WHERE so every run guarantees
-- the surrogate key for guest/unresolved orders exists. The unique_key='customer_key'
-- delete+insert strategy in DuckDB incremental prevents duplicate sentinel rows —
-- delete removes the old sentinel by customer_key, then insert re-adds exactly one.
-- WARNING: this relies on DuckDB incremental dedup semantics. A test (see schema.yml)
-- validates exactly-one 'Unknown' row on each dbt test run.
-- NOT exported to the Serving Layer (Metabase) — use dim_customers instead.
UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as customer_key,
    'Unknown' as customer_id,
    CAST(NULL AS VARCHAR) as customer_code,
    'Unknown' as full_name,
    'Unknown' as email,
    'Unknown' as phone,
    NULL as status,
    NULL as birth_date,
    'Unknown' as gender,
    'Unknown' as customer_group,
    NULL as customer_group_id,
    NULL as customer_group_code,
    NULL as customer_group_name,
    0 as loyalty_points,
    'Unknown' as city,
    'Unknown' as province,
    'Unknown' as district,
    'Unknown' as ward,
    'Unknown' as address1,
    'Unknown' as country,
    NULL as address2,
    NULL as zip,
    NULL as company,
    NULL as address_phone,
    NULL as assignee_id,
    NULL as tax_number,
    NULL as website,
    NULL as description,
    NULL as default_discount_rate,
    NULL as default_price_list_id,
    NULL as debt,
    NULL as loyalty_customer_json,
    NULL as social_customers_json,
    NULL as created_at,
    NULL as updated_at

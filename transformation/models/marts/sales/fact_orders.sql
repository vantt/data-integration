{{ config(
    tags=['mart', 'fact'],
    materialized='incremental',
    unique_key='order_id',
    options={'format': 'parquet'}
) }}

WITH orders AS (
    SELECT * FROM {{ ref('std_orders') }}
    {% if is_incremental() %}
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),

valid_customers AS (
    SELECT customer_key FROM {{ ref('dim_customers') }}
)

SELECT
    -- Keys
    orders.order_id,
    COALESCE(vc.customer_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as customer_key,
    CASE 
        WHEN shipping_province IS NULL THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(['shipping_province', 'shipping_district', 'shipping_ward', "coalesce(shipping_country, 'Vietnam')"]) }}
    END as shipping_geography_key,

    CASE 
        WHEN billing_province IS NULL THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(['billing_province', 'billing_district', 'billing_ward', "coalesce(billing_country, 'Vietnam')"]) }}
    END as billing_geography_key,

    -- Full Address Strings
    coalesce(shipping_address1, '') || ', ' || coalesce(shipping_ward, '') || ', ' || coalesce(shipping_district, '') || ', ' || coalesce(shipping_province, '') || ', ' || coalesce(shipping_country, 'Vietnam') as shipping_address,
    coalesce(billing_address1, '') || ', ' || coalesce(billing_ward, '') || ', ' || coalesce(billing_district, '') || ', ' || coalesce(billing_province, '') || ', ' || coalesce(billing_country, 'Vietnam') as billing_address,
    -- Note: Orders can have multiple promotions. To keep 1:1, we might pick the primary one 
    -- or just bridge it later. For now, we leave NULL or specific handling if needed. 
    -- Simplification: Just take the first code if present, or NULL.
    {{ dbt_utils.generate_surrogate_key(["json_extract_string(json_extract_string(discount_codes, '$[0]'), '$.code')"]) }} as promotion_key,
    {{ dbt_utils.generate_surrogate_key(['location_id']) }} as branch_location_key,
    {{ dbt_utils.generate_surrogate_key(["coalesce(channel, 'Unknown')"]) }} as channel_key,
    COALESCE(ds.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as staff_key,
    {{ dbt_utils.generate_surrogate_key(['status']) }} as status_key,
    coalesce(cast(strftime(created_at, '%Y%m%d') as integer), 19000101) as date_key,
    
    -- Status Metrics
    status,
    payment_status,
    fulfillment_status,
    
    -- Financial Metrics
    total_amount as gmv,
    total_discount_amount,
    total_tax_amount,
    
    -- Performance Metrics
    -- timestamps difference in hours
    date_diff('hour', created_at, completed_at) as time_to_complete_hours,
    
    created_at as order_timestamp,
    updated_at

FROM orders
LEFT JOIN valid_customers vc ON {{ dbt_utils.generate_surrogate_key(["coalesce(cast(orders.customer_id as varchar), 'Unknown')"]) }} = vc.customer_key
LEFT JOIN {{ ref('dim_staff') }} ds ON {{ dbt_utils.generate_surrogate_key(['orders.salesperson_id']) }} = ds.staff_key

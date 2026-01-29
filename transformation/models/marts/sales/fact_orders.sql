{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

WITH orders AS (
    SELECT * FROM {{ ref('std_orders') }}

),

valid_customers AS (
    SELECT customer_key FROM {{ ref('dim_customers_base') }}
)

SELECT
    -- Keys
    orders.order_id,
    COALESCE(vc.customer_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as customer_key,
    CASE 
        WHEN shipping_province IS NULL OR shipping_province = '' OR shipping_province = 'Unknown' THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["trim(coalesce(shipping_province, ''))", "trim(coalesce(shipping_district, ''))", "trim(coalesce(shipping_ward, ''))", "trim(coalesce(shipping_country, 'Vietnam'))"]) }}
    END as shipping_geography_key,

    CASE 
        WHEN billing_province IS NULL OR billing_province = '' OR billing_province = 'Unknown' THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["trim(coalesce(billing_province, ''))", "trim(coalesce(billing_district, ''))", "trim(coalesce(billing_ward, ''))", "trim(coalesce(billing_country, 'Vietnam'))"]) }}
    END as billing_geography_key,

    -- Full Address Strings
    concat_ws(', ', nullif(shipping_address1, ''), nullif(shipping_ward, ''), nullif(shipping_district, ''), nullif(shipping_province, ''), coalesce(nullif(shipping_country, ''), 'Vietnam')) as shipping_address,
    concat_ws(', ', nullif(billing_address1, ''), nullif(billing_ward, ''), nullif(billing_district, ''), nullif(billing_province, ''), coalesce(nullif(billing_country, ''), 'Vietnam')) as billing_address,
    
    -- Note: Orders can have multiple promotions. To keep 1:1, we might pick the primary one 
    -- or just bridge it later. For now, we leave NULL or specific handling if needed. 
    -- Simplification: Just take the first code if present, or NULL.
    {{ dbt_utils.generate_surrogate_key(["coalesce(json_extract_string(json_extract_string(discount_codes, '$[0]'), '$.code'), 'Unknown')"]) }} as promotion_key,
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

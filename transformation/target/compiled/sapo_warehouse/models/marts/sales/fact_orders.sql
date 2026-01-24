

WITH orders AS (
    SELECT * FROM "data_integration2"."main_staging"."std_orders"
),

valid_customers AS (
    SELECT customer_key FROM "data_integration2"."main_marts"."dim_customers"
)

SELECT
    -- Keys
    orders.order_id,
    COALESCE(vc.customer_key, md5('Unknown')) as customer_key,
    md5(
        CASE 
            WHEN shipping_province IS NULL THEN 'Unknown'
            ELSE
                coalesce(shipping_province,'') || '-' || 
                coalesce(shipping_district,'') || '-' || 
                coalesce(shipping_ward,'') || '-' ||
                coalesce(shipping_country, 'Vietnam')
        END
    ) as shipping_geography_key,

    md5(
        CASE 
            WHEN billing_province IS NULL THEN 'Unknown'
            ELSE
                coalesce(billing_province,'') || '-' || 
                coalesce(billing_district,'') || '-' || 
                coalesce(billing_ward,'') || '-' ||
                coalesce(billing_country, 'Vietnam')
        END
    ) as billing_geography_key,

    -- Full Address Strings
    coalesce(shipping_address1, '') || ', ' || coalesce(shipping_ward, '') || ', ' || coalesce(shipping_district, '') || ', ' || coalesce(shipping_province, '') || ', ' || coalesce(shipping_country, 'Vietnam') as shipping_address,
    coalesce(billing_address1, '') || ', ' || coalesce(billing_ward, '') || ', ' || coalesce(billing_district, '') || ', ' || coalesce(billing_province, '') || ', ' || coalesce(billing_country, 'Vietnam') as billing_address,
    -- Note: Orders can have multiple promotions. To keep 1:1, we might pick the primary one 
    -- or just bridge it later. For now, we leave NULL or specific handling if needed. 
    -- Simplification: Just take the first code if present, or NULL.
    md5(json_extract_string(json_extract_string(discount_codes, '$[0]'), '$.code')) as promotion_key,
    md5(cast(location_id as string)) as branch_location_key,
    md5(channel) as channel_key,
    md5(salesperson_id) as staff_key,
    md5(status) as status_key,
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
    
    created_at as order_timestamp

FROM orders
LEFT JOIN valid_customers vc ON md5(coalesce(cast(orders.customer_id as varchar), 'Unknown')) = vc.customer_key
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
),

source_definitions AS (
    SELECT id, is_generic_source FROM {{ ref('ref_order_sources') }}
),

first_shipment AS (
    SELECT order_id, MIN(shipped_at) as first_shipped_at
    FROM {{ ref('std_fulfillments') }}
    WHERE shipped_at IS NOT NULL
    GROUP BY order_id
)

SELECT
    -- Keys
    orders.order_id,
    orders.order_code,
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

    -- Channel Key Logic
    CASE
        WHEN sd.is_generic_source = true THEN
            {{ dbt_utils.generate_surrogate_key(['cast(source_id as string)', "coalesce(cast(location_id as string), 'Unknown')"]) }}
        ELSE
            {{ dbt_utils.generate_surrogate_key(['cast(source_id as string)', "'Unknown'"]) }}
    END as channel_key,

    COALESCE(ds.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as staff_key,
    {{ dbt_utils.generate_surrogate_key(['status']) }} as status_key,
    coalesce(cast(strftime(created_at, '%Y%m%d') as integer), 19000101) as date_key,
    (extract(hour from created_at) * 100) + extract(minute from created_at) as time_key,
    
    -- Status Metrics
    status,
    payment_status,
    fulfillment_status,
    
    -- Financial Metrics (Revenue Waterfall)
    -- See: docs/analytics-handbook/guides/revenue_terminology.md
    total_amount + total_discount_amount as gross_revenue,    -- Giá niêm yết = SUM(price × qty), trước chiết khấu & thuế
    total_discount_amount as discount_amount,                -- Chiết khấu
    total_amount as net_revenue,                             -- Doanh thu thuần (sau chiết khấu, trước thuế) = Sapo $.total
    total_tax_amount as tax_amount,                          -- Thuế VAT
    total_amount + total_tax_amount as total_collected,      -- Tổng thu từ khách (sau chiết khấu, gồm thuế)
    
    -- Performance Metrics
    fs.first_shipped_at,                                     -- Ngày xuất kho đầu tiên
    date_diff('hour', created_at, completed_at) as time_to_complete_hours,
    
    orders.client_details,
    orders.discount_codes,
    
    created_at as order_timestamp,
    updated_at

FROM orders
LEFT JOIN valid_customers vc ON {{ dbt_utils.generate_surrogate_key(["coalesce(cast(orders.customer_id as varchar), 'Unknown')"]) }} = vc.customer_key
LEFT JOIN {{ ref('dim_staff') }} ds ON {{ dbt_utils.generate_surrogate_key(['orders.salesperson_id']) }} = ds.staff_key
LEFT JOIN source_definitions sd ON orders.source_id = sd.id
LEFT JOIN first_shipment fs ON orders.order_id = fs.order_id

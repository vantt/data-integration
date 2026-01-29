{{ config(
    tags=['mart', 'fact'],
    location="{{ get_rolling_location() }}"
) }}

WITH items AS (
    SELECT * FROM {{ ref('std_order_items') }}
),
orders AS (
    SELECT * FROM {{ ref('std_orders') }}

),
valid_customers AS (
    SELECT customer_key FROM {{ ref('dim_customers_base') }}
)

SELECT
    -- Surrogate Keys (Foreign Keys to Dims)
    CASE 
        WHEN i.product_id IS NULL OR i.product_id = '' THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["i.product_id || '-' || coalesce(i.variant_id, '')"]) }}
    END as product_key,
    {{ dbt_utils.generate_surrogate_key(["coalesce(i.product_type, 'Unknown')"]) }} as category_key,
    COALESCE(vc.customer_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as customer_key,
    {{ dbt_utils.generate_surrogate_key(['cast(o.location_id as string)']) }} as branch_location_key,
    {{ dbt_utils.generate_surrogate_key(["coalesce(o.channel, 'Unknown')"]) }} as channel_key,
    COALESCE(ds.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as staff_key,
    {{ dbt_utils.generate_surrogate_key(['o.status']) }} as status_key,
    coalesce(cast(strftime(o.created_at, '%Y%m%d') as integer), 19000101) as date_key, -- Link to dim_date YYYYMMDD
    
    -- Degenerate Keys
    i.order_id,
    i.item_id,
    
    -- Metrics
    i.quantity,
    i.total_price as revenue,
    i.weight_grams,
    
    -- Addresses
    -- Addresses
    CASE 
        WHEN o.shipping_province IS NULL THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["coalesce(o.shipping_province,'')", "coalesce(o.shipping_district,'')", "coalesce(o.shipping_ward,'')", "coalesce(o.shipping_country, 'Vietnam')"]) }}
    END as shipping_geography_key,

    CASE 
        WHEN o.billing_province IS NULL THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["coalesce(o.billing_province,'')", "coalesce(o.billing_district,'')", "coalesce(o.billing_ward,'')", "coalesce(o.billing_country, 'Vietnam')"]) }}
    END as billing_geography_key,
    
    -- Pro-rated amounts (Simple logic for now)
    -- Ideally we'd allocate order-level discount to items here
    
    o.created_at as sol_timestamp,
    o.updated_at

FROM items i
JOIN orders o ON i.order_id = o.order_id
LEFT JOIN valid_customers vc ON {{ dbt_utils.generate_surrogate_key(['o.customer_id']) }} = vc.customer_key
LEFT JOIN {{ ref('dim_staff') }} ds ON {{ dbt_utils.generate_surrogate_key(['o.salesperson_id']) }} = ds.staff_key

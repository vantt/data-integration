

WITH items AS (
    SELECT * FROM "data_integration2"."main_staging"."std_order_items"
),
orders AS (
    SELECT * FROM "data_integration2"."main_staging"."std_orders"
),
valid_customers AS (
    SELECT customer_key FROM "data_integration2"."main_marts"."dim_customers"
)

SELECT
    -- Surrogate Keys (Foreign Keys to Dims)
    md5(i.product_id || '-' || i.variant_id) as product_key,
    md5(coalesce(i.product_type, 'Uncategorized')) as category_key,
    COALESCE(vc.customer_key, md5('Unknown')) as customer_key,
    md5(cast(o.location_id as string)) as branch_location_key,
    md5(o.channel) as channel_key,
    COALESCE(ds.staff_key, md5('Unknown')) as staff_key,
    md5(o.status) as status_key,
    coalesce(cast(strftime(o.created_at, '%Y%m%d') as integer), 19000101) as date_key, -- Link to dim_date YYYYMMDD
    
    -- Degenerate Keys
    i.order_id,
    i.item_id,
    
    -- Metrics
    i.quantity,
    i.total_price as revenue,
    i.weight_grams,
    
    -- Addresses
    md5(
        CASE 
            WHEN o.shipping_province IS NULL THEN 'Unknown'
            ELSE
                coalesce(o.shipping_province,'') || '-' || 
                coalesce(o.shipping_district,'') || '-' || 
                coalesce(o.shipping_ward,'') || '-' ||
                coalesce(o.shipping_country, 'Vietnam')
        END
    ) as shipping_geography_key,

    md5(
        CASE 
            WHEN o.billing_province IS NULL THEN 'Unknown'
            ELSE
                coalesce(o.billing_province,'') || '-' || 
                coalesce(o.billing_district,'') || '-' || 
                coalesce(o.billing_ward,'') || '-' ||
                coalesce(o.billing_country, 'Vietnam')
        END
    ) as billing_geography_key,
    
    -- Pro-rated amounts (Simple logic for now)
    -- Ideally we'd allocate order-level discount to items here
    
    o.created_at as sol_timestamp

FROM items i
JOIN orders o ON i.order_id = o.order_id
LEFT JOIN valid_customers vc ON md5(o.customer_id) = vc.customer_key
LEFT JOIN "data_integration2"."main_marts"."dim_staff" ds ON md5(o.salesperson_id) = ds.staff_key
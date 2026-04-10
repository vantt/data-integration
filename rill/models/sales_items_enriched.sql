SELECT
    s.order_id,
    s.item_id,
    CAST(s.sol_timestamp AS TIMESTAMP) AS sale_timestamp,
    date_trunc('day', s.sol_timestamp) AS sale_date,
    EXTRACT(HOUR FROM s.sol_timestamp) AS sale_hour,
    strftime(s.sol_timestamp, '%a') AS day_of_week,
    p.product_name,
    p.variant_name,
    p.sku,
    p.barcode,
    p.product_type,
    COALESCE(p.brand_name, 'Unknown') AS brand_name,
    c.channel_name,
    c.channel_category,
    c.platform,
    b.branch_location_name,
    b.branch_location_code,
    g.province,
    g.district,
    st.full_name AS staff_name,
    os.status_code AS status,
    s.quantity,
    s.revenue,
    s.discount_amount,
    s.distributed_discount_amount,
    COALESCE(s.discount_amount, 0) + COALESCE(s.distributed_discount_amount, 0) AS total_discount_amount,
    s.weight_grams
FROM src_fact_sales s
LEFT JOIN src_dim_products p ON s.product_key = p.product_key
LEFT JOIN src_dim_channels c ON s.channel_key = c.channel_key
LEFT JOIN src_dim_branch_location b ON s.branch_location_key = b.branch_location_key
LEFT JOIN src_dim_geography g ON s.shipping_geography_key = g.geography_key
LEFT JOIN src_dim_staff st ON s.staff_key = st.staff_key
LEFT JOIN src_dim_order_status os ON s.status_key = os.status_key

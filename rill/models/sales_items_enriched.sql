SELECT
    s.order_id,
    s.order_line_id,
    s.sol_timestamp AS sale_timestamp,
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
    c.channel_format,
    c.platform,
    c.channel_brand,
    c.market,
    c.source_type,
    COALESCE(c.is_sales_channel, false) AS is_sales_channel,
    b.branch_location_name,
    b.branch_location_code,
    g.province,
    g.district,
    -- Customer segmentation (3-layer scope architecture)
    COALESCE(cu.customer_type, 'RETAIL') AS customer_type,
    COALESCE(cu.value_group, 'VALUE_BRONZE') AS value_group,
    cu.customer_status,
    -- Sales attribution: seller (assignee) primary; creator (account) for ops views.
    seller.full_name AS seller_name,
    creator.full_name AS creator_name,
    os.status_code AS status,
    s.quantity,
    s.revenue,
    s.discount_amount,
    s.distributed_discount_amount,
    COALESCE(s.discount_amount, 0) + COALESCE(s.distributed_discount_amount, 0) AS total_discount_amount,
    s.weight_grams,
    -- Scope flags for 3-layer architecture (see report_segmentation.md)
    COALESCE(c.is_sales_channel, false) AND os.status_code NOT IN ('CANCELLED', 'Voided') AS scope_sales,
    COALESCE(c.is_sales_channel, false) AND os.status_code NOT IN ('CANCELLED', 'Voided') AND COALESCE(cu.customer_type, 'RETAIL') = 'RETAIL' AS scope_retail,
    COALESCE(c.is_sales_channel, false) AND os.status_code NOT IN ('CANCELLED', 'Voided') AND COALESCE(cu.customer_type, 'RETAIL') IN ('WHOLESALE', 'PARTNER') AS scope_b2b
FROM src_fact_sales s
LEFT JOIN src_dim_products p ON s.product_key = p.product_key
LEFT JOIN src_dim_channels c ON s.channel_key = c.channel_key
LEFT JOIN src_dim_branch_location b ON s.branch_location_key = b.branch_location_key
LEFT JOIN src_dim_geography g ON s.shipping_geography_key = g.geography_key
LEFT JOIN src_dim_customers cu ON s.customer_key = cu.customer_key
LEFT JOIN src_dim_staff seller ON s.seller_staff_key = seller.staff_key
LEFT JOIN src_dim_staff creator ON s.creator_staff_key = creator.staff_key
LEFT JOIN src_dim_order_status os ON s.status_key = os.status_key

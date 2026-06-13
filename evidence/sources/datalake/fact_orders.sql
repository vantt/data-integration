SELECT
    order_id,
    order_code,
    status,
    ordered_at,
    customer_key,
    channel_key,
    gross_revenue,
    net_revenue,
    discount_amount,
    scope_sales,
    is_active_order
FROM main_marts.fact_orders

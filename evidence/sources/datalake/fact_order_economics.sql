SELECT
    order_id,
    channel_key,
    scope_sales,
    has_cogs,
    is_active_order,
    channel_net_profit,
    gross_profit,
    net_revenue
FROM main_marts.fact_order_economics

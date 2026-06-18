"""SQL constants for customer dim_customers segments + aggregated value metrics."""

DIM_BY_CUSTOMER_ID = """
SELECT
    customer_key,
    lifecycle_stage,
    product_affinity,
    payment_behavior,
    geo_region,
    customer_type,
    first_order_date
FROM main_marts.dim_customers
WHERE customer_id = CAST(? AS VARCHAR)
LIMIT 1
"""

VALUE_METRICS_BY_CUSTOMER_KEY = """
SELECT
    SUM(fo.total_collected)                                       AS lifetime_value,
    COUNT(DISTINCT fo.order_id)                                   AS order_count,
    SUM(foe.gross_profit)                                         AS total_gross_profit,
    SUM(foe.cogs_amount)                                          AS total_cogs,
    AVG(foe.gross_margin_pct)                                     AS avg_gross_margin_pct,
    SUM(foe.return_amount)                                        AS total_return_amount,
    SUM(COALESCE(foe.return_count, 0))                            AS return_count,
    COUNT(DISTINCT CASE WHEN foe.has_cogs THEN fo.order_id END)   AS cogs_order_count
FROM main_marts.fact_orders fo
LEFT JOIN main_marts.fact_order_economics foe ON fo.order_id = foe.order_id
WHERE fo.customer_key = ?
"""

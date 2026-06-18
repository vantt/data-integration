"""SQL constants for customer order history queries from olap.duckdb."""

# Fetch up to 50 orders for a customer, newest first.
# customer_key resolved inline via dim_customers to avoid a second round-trip.
# Payment: subquery with LIMIT 1 (is_primary may not exist on all schemas).
ORDERS_BY_CUSTOMER_ID = """
SELECT
    fo.order_code,
    CAST(fo.ordered_at AS VARCHAR)          AS created_at,
    fo.status,
    COALESCE(ch.channel_name, '')           AS channel_name,
    COALESCE(s.full_name, '')               AS seller_name,
    CAST(fo.total_collected AS DOUBLE)      AS total_collected,
    CAST(foe.gross_profit AS DOUBLE)        AS gross_profit,
    CAST(foe.gross_margin_pct AS DOUBLE)    AS gross_margin_pct,
    COALESCE(
        (SELECT pm.payment_method_name
         FROM main_marts.fact_payments fp2
         JOIN main_marts.dim_payment_methods pm
           ON pm.payment_method_key = fp2.payment_method_key
         WHERE fp2.order_id = fo.order_id
         LIMIT 1),
        ''
    )                                       AS payment_label,
    EXISTS (
        SELECT 1
        FROM main_marts.fact_order_returns r
        WHERE r.order_code = fo.order_code
    )                                       AS has_return
FROM main_marts.fact_orders fo
JOIN main_marts.dim_customers dc
    ON dc.customer_id = CAST(? AS VARCHAR)
   AND dc.customer_key = fo.customer_key
LEFT JOIN main_marts.fact_order_economics foe
    ON foe.order_id = fo.order_id
LEFT JOIN main_marts.dim_channels ch
    ON ch.channel_key = fo.channel_key
LEFT JOIN main_marts.dim_staff s
    ON s.staff_key = fo.seller_staff_key
ORDER BY fo.ordered_at DESC
LIMIT 50
"""

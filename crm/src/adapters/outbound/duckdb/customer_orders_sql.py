"""SQL constants for customer order history queries from olap.duckdb."""

# Fetch up to 50 orders for a customer, newest first.
# customer_key resolved inline via dim_customers to avoid a second round-trip.
# payment_label: pre-aggregated LEFT JOIN (ANY_VALUE per order_id) replaces the
# per-row correlated scalar subquery that ran N extra lookups per result row.
# has_return: DISTINCT order_code lookup replaces per-row EXISTS.
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
    COALESCE(pay.payment_method_name, '')   AS payment_label,
    (ret.order_code IS NOT NULL)            AS has_return
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
LEFT JOIN (
    SELECT fp.order_id, ANY_VALUE(pm.payment_method_name) AS payment_method_name
    FROM main_marts.fact_payments fp
    JOIN main_marts.dim_payment_methods pm
        ON pm.payment_method_key = fp.payment_method_key
    WHERE fp.order_id IS NOT NULL
    GROUP BY fp.order_id
) pay ON pay.order_id = fo.order_id
LEFT JOIN (
    SELECT DISTINCT order_code
    FROM main_marts.fact_order_returns
) ret ON ret.order_code = fo.order_code
ORDER BY fo.ordered_at DESC
LIMIT 50
"""

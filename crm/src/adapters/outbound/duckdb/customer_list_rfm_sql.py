"""SQL for batch Recency / Frequency / customer_type lookup — S02 customer list.

One query joins dim_customers + fact_orders for all party_ids on the page.
Parameters: a Python list[str] of stringified Sapo customer_ids.
Returns one row per customer_id found in dim_customers.
"""

BATCH_RFM = """
SELECT
    dc.customer_id                                                        AS customer_id,
    dc.customer_type                                                      AS customer_type,
    MAX(fo.ordered_at)::DATE::VARCHAR                                     AS last_order_date,
    COUNT(DISTINCT fo.order_id)                                           AS order_count
FROM main_marts.dim_customers dc
LEFT JOIN main_marts.fact_orders fo ON fo.customer_key = dc.customer_key
WHERE dc.customer_id IN (SELECT unnest(?::VARCHAR[]))
GROUP BY dc.customer_id, dc.customer_type
"""

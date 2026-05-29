-- Return events for one order. Joined on order_code (NOT order_id) — see researcher-01 §3:
-- fact_order_returns links back by order_code. Case-insensitive to match header lookup.
SELECT
    return_date,
    refund_amount,
    return_quantity,
    return_status,
    refund_status,
    return_reason
FROM fact_order_returns
WHERE UPPER(order_code) = UPPER(?)
ORDER BY return_date;

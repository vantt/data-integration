-- Payments for one order: fact_payments x dim_payment_methods (by payment_method_key),
-- joined on order_id.
SELECT
    pm.payment_method_name,
    pm.payment_method_type,
    fp.amount,
    fp.status,
    fp.payment_timestamp,
    fp.paid_on
FROM fact_payments fp
LEFT JOIN dim_payment_methods pm ON fp.payment_method_key = pm.payment_method_key
WHERE fp.order_id = ?
ORDER BY fp.payment_timestamp;

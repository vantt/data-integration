-- Fetch the top action for a customer from mart_customer_action_queue.
-- Returns at most 1 row (each customer has one action_type).
-- Degrades gracefully to [] if view absent (optional collection).
SELECT
    action_type,
    priority_rank,
    action_rationale,
    value_at_stake,
    avg_order_value,
    avg_days_between_orders,
    next_purchase_signal,
    discount_sensitivity,
    predicted_next_purchase_date,
    cancel_rate,
    recency_days
FROM mart_customer_action_queue
WHERE customer_key = ?
ORDER BY priority_rank
LIMIT 1;

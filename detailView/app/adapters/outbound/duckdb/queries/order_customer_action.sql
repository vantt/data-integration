-- Fetch the top outreach action for the customer linked to an order.
-- Joins via customer_key (from the order header). Returns at most 1 row.
-- Degrades gracefully to [] if mart_customer_action_queue is absent.
SELECT
    action_type,
    action_rationale,
    priority_rank
FROM mart_customer_action_queue
WHERE customer_key = ?
ORDER BY priority_rank
LIMIT 1;

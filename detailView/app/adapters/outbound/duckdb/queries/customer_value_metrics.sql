-- Aggregated value metrics over a customer's orders (by customer_key).
-- LTV from total_collected; profit/cogs sums + avg margin from economics; returns;
-- cogs_order_count = orders where has_cogs (for the coverage caveat in the UI).
SELECT
    SUM(fo.total_collected)                                       AS lifetime_value,
    COUNT(DISTINCT fo.order_id)                                   AS total_orders_count,
    SUM(foe.gross_profit)                                         AS total_gross_profit,
    SUM(foe.cogs_amount)                                          AS total_cogs,
    AVG(foe.gross_margin_pct)                                     AS avg_gross_margin_pct,
    SUM(foe.return_amount)                                        AS total_return_amount,
    SUM(COALESCE(foe.return_count, 0))                            AS return_count,
    COUNT(DISTINCT CASE WHEN foe.has_cogs THEN fo.order_id END)   AS cogs_order_count
FROM fact_orders fo
LEFT JOIN fact_order_economics foe ON fo.order_id = foe.order_id
WHERE fo.customer_key = ?;

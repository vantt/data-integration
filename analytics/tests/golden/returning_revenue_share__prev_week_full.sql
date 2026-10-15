SELECT
  ((SELECT COALESCE(SUM(m.net_revenue), 0)
   FROM main_marts.fact_orders AS m
   LEFT JOIN main_marts.dim_customers AS j_customers ON m.customer_key = j_customers.customer_key
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST((CAST(date_trunc('week', DATE '2026-10-11') AS DATE) - 7) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order
     AND CAST(timezone('Asia/Ho_Chi_Minh', j_customers.first_order_date) AS DATE) < (CAST(date_trunc('week', DATE '2026-10-11') AS DATE) - 7)) * 100.0 / NULLIF((SELECT COALESCE(SUM(m.net_revenue), 0)
   FROM main_marts.fact_orders AS m
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST((CAST(date_trunc('week', DATE '2026-10-11') AS DATE) - 7) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order), 0)) AS returning_revenue_share

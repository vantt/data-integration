SELECT
  (SELECT COALESCE(SUM(m.net_revenue), 0)
   FROM main_marts.fact_orders AS m
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', (CAST(timezone('Asia/Ho_Chi_Minh', now()) AS DATE) - 1)) AS DATE) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST(((CAST(timezone('Asia/Ho_Chi_Minh', now()) AS DATE) - 1) + 1) AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order) AS net_sales

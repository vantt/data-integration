SELECT
  ((SELECT COUNT(DISTINCT m.order_id)
   FROM main_marts.fact_order_economics AS m
   LEFT JOIN main_marts.fact_orders AS j_orders ON m.order_id = j_orders.order_id
   WHERE j_orders.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST((CAST(date_trunc('week', DATE '2026-10-11') AS DATE) - 7) AS TIMESTAMP))
     AND j_orders.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order
     AND m.has_cogs) * 100.0 / NULLIF((SELECT COUNT(DISTINCT m.order_id)
   FROM main_marts.fact_orders AS m
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST((CAST(date_trunc('week', DATE '2026-10-11') AS DATE) - 7) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order), 0)) AS cogs_coverage_pct

SELECT
  ((SELECT COALESCE(SUM(m.discount_amount), 0)
   FROM main_marts.fact_orders AS m
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST((DATE '2026-10-11' + 1) AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order) * 100.0 / NULLIF((SELECT COALESCE(SUM(m.gross_revenue), 0)
   FROM main_marts.fact_orders AS m
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST((DATE '2026-10-11' + 1) AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order), 0)) AS discount_rate

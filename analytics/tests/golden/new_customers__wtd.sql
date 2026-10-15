SELECT
  (SELECT COUNT(DISTINCT m.customer_key)
   FROM main_marts.dim_customers AS m
   WHERE m.first_order_date >= timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.first_order_date < timezone('Asia/Ho_Chi_Minh', CAST((DATE '2026-10-11' + 1) AS TIMESTAMP))) AS new_customers

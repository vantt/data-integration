SELECT
  (SELECT COUNT(DISTINCT m.return_id)
   FROM main_marts.fact_order_returns AS m
   LEFT JOIN main_marts.dim_channels AS j_channels ON m.channel_key = j_channels.channel_key
   WHERE m.returned_at >= timezone('Asia/Ho_Chi_Minh', CAST((CAST(date_trunc('week', DATE '2026-10-11') AS DATE) - 7) AS TIMESTAMP))
     AND m.returned_at < timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('week', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND j_channels.is_sales_channel
     AND m.return_status = 'returned') AS return_count

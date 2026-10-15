SELECT
  ((CASE WHEN ((SELECT NULLIF(SUM(m.target_val), 0)
   FROM main_marts.fact_targets AS m
   WHERE m.cycle_start_date <= DATE '2026-10-11'
     AND m.cycle_end_date >= DATE '2026-10-11'
     AND m.metric_code = 'gmv') - (SELECT COALESCE(SUM(m.gross_revenue), 0)
   FROM main_marts.fact_orders AS m
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('month', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST(DATE '2026-10-11' AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order)) < 0 THEN 0 ELSE ((SELECT NULLIF(SUM(m.target_val), 0)
   FROM main_marts.fact_targets AS m
   WHERE m.cycle_start_date <= DATE '2026-10-11'
     AND m.cycle_end_date >= DATE '2026-10-11'
     AND m.metric_code = 'gmv') - (SELECT COALESCE(SUM(m.gross_revenue), 0)
   FROM main_marts.fact_orders AS m
   WHERE m.ordered_at >= timezone('Asia/Ho_Chi_Minh', CAST(CAST(date_trunc('month', DATE '2026-10-11') AS DATE) AS TIMESTAMP))
     AND m.ordered_at < timezone('Asia/Ho_Chi_Minh', CAST(DATE '2026-10-11' AS TIMESTAMP))
     AND m.scope_sales
     AND m.is_active_order)) END) / NULLIF(GREATEST(EXTRACT(DAY FROM last_day(DATE '2026-10-11')) - EXTRACT(DAY FROM DATE '2026-10-11'), 1), 0)) AS gmv_required_daily_run_rate

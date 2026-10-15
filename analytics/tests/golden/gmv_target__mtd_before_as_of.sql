SELECT
  (SELECT NULLIF(SUM(m.target_val), 0)
   FROM main_marts.fact_targets AS m
   WHERE m.cycle_start_date <= DATE '2026-10-11'
     AND m.cycle_end_date >= DATE '2026-10-11'
     AND m.metric_code = 'gmv') AS gmv_target

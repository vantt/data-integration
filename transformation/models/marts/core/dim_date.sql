{{ config(
    tags=['mart', 'dim']
) }}

WITH date_spine AS (
  {{ dbt_utils.date_spine(
      datepart="day",
      start_date="cast('2010-01-01' as date)",
      end_date="cast('2030-12-31' as date)"
     )
  }}
)

SELECT
    cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
    date_day as date_actual,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(quarter from date_day) as quarter,
    extract(dayofweek from date_day) as day_of_week,
    -- strftime('%A', date_day) as day_name, -- DuckDB specific
    -- strftime('%B', date_day) as month_name
    case when extract(dayofweek from date_day) in (0, 6) then true else false end as is_weekend

FROM date_spine

UNION ALL

SELECT
    19000101 as date_key,
    cast('1900-01-01' as date) as date_actual,
    1900 as year,
    1 as month,
    1 as quarter,
    1 as day_of_week,
    false as is_weekend

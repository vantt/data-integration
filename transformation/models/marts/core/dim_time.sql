{{ config(
    tags=['mart', 'dim']
) }}

WITH min_spawn AS (
    -- =============================================================================================
    -- TIME GENERATION
    -- =============================================================================================
    -- Generates 1 row per minute for 24 hours = 1,440 rows.
    -- Better than "Seconds" (too heavy) and "Hours" (too vague).
    -- Uses DuckDB's generate_series for in-memory generation (no seeds needed).
    SELECT 
        unnest(generate_series(
            TIMESTAMP '2000-01-01 00:00:00',
            TIMESTAMP '2000-01-01 23:59:00',
            INTERVAL 1 MINUTE
        )) as time_val
)

SELECT
    -- Key: HHMM format (e.g. 0930, 2359)
    (extract(hour from time_val) * 100) + extract(minute from time_val) as time_key,
    
    -- Attributes
    strftime(time_val, '%H:%M') as time_of_day_24,
    strftime(time_val, '%I:%M %p') as time_of_day_12,
    extract(hour from time_val) as hour_24,
    extract(hour from time_val) % 12 as hour_12,
    extract(minute from time_val) as minute,
    
    CASE 
        WHEN extract(hour from time_val) < 12 THEN 'AM' 
        ELSE 'PM' 
    END as am_pm,
    
    -- Business Logic (Legacy Migration)
    CASE 
        WHEN extract(hour from time_val) >= 9 AND extract(hour from time_val) < 17 THEN TRUE 
        ELSE FALSE 
    END as is_business_hour,
    
    CASE 
        -- Lunch Peak: 11:00 - 14:00
        -- Dinner Peak: 16:00 - 19:00
        WHEN extract(hour from time_val) >= 11 AND extract(hour from time_val) < 14 THEN TRUE
        WHEN extract(hour from time_val) >= 16 AND extract(hour from time_val) < 19 THEN TRUE
        ELSE FALSE
    END as is_peak_hour,
    
    CASE
        WHEN extract(hour from time_val) >= 5 AND extract(hour from time_val) < 12 THEN 'Morning'
        WHEN extract(hour from time_val) >= 12 AND extract(hour from time_val) < 17 THEN 'Afternoon'
        WHEN extract(hour from time_val) >= 17 AND extract(hour from time_val) < 21 THEN 'Evening'
        ELSE 'Night'
    END as day_period

FROM min_spawn

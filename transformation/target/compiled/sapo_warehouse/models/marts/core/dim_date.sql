

WITH date_spine AS (
  





with rawdata as (

    

    

    with p as (
        select 0 as generated_number union all select 1
    ), unioned as (

    select

    
    p0.generated_number * power(2, 0)
     + 
    
    p1.generated_number * power(2, 1)
     + 
    
    p2.generated_number * power(2, 2)
     + 
    
    p3.generated_number * power(2, 3)
     + 
    
    p4.generated_number * power(2, 4)
     + 
    
    p5.generated_number * power(2, 5)
     + 
    
    p6.generated_number * power(2, 6)
     + 
    
    p7.generated_number * power(2, 7)
     + 
    
    p8.generated_number * power(2, 8)
     + 
    
    p9.generated_number * power(2, 9)
     + 
    
    p10.generated_number * power(2, 10)
     + 
    
    p11.generated_number * power(2, 11)
     + 
    
    p12.generated_number * power(2, 12)
    
    
    + 1
    as generated_number

    from

    
    p as p0
     cross join 
    
    p as p1
     cross join 
    
    p as p2
     cross join 
    
    p as p3
     cross join 
    
    p as p4
     cross join 
    
    p as p5
     cross join 
    
    p as p6
     cross join 
    
    p as p7
     cross join 
    
    p as p8
     cross join 
    
    p as p9
     cross join 
    
    p as p10
     cross join 
    
    p as p11
     cross join 
    
    p as p12
    
    

    )

    select *
    from unioned
    where generated_number <= 7669
    order by generated_number



),

all_periods as (

    select (
        

    (cast('2010-01-01' as date) + cast(row_number() over (order by 1) - 1 as bigint) * interval 1 day)
    ) as date_day
    from rawdata

),

filtered as (

    select *
    from all_periods
    where date_day <= cast('2030-12-31' as date)

)

select * from filtered


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
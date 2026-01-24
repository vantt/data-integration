
    
    

with all_values as (

    select
        status as value_field,
        count(*) as n_records

    from "data_integration2"."main_staging"."std_fulfillments"
    group by status

)

select *
from all_values
where value_field not in (
    'DELIVERED','SHIPPING','PACKED','CANCELLED','FAILED','PENDING'
)



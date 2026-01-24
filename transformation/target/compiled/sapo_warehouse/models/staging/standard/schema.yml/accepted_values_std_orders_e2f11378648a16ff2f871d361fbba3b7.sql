
    
    

with all_values as (

    select
        payment_status as value_field,
        count(*) as n_records

    from "data_integration2"."main_staging"."std_orders"
    group by payment_status

)

select *
from all_values
where value_field not in (
    'PAID','PENDING','PARTIALLY_PAID','REFUNDED','VOIDED','UNPAID'
)



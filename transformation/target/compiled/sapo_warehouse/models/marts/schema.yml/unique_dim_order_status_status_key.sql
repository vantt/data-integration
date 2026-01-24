
    
    

select
    status_key as unique_field,
    count(*) as n_records

from "data_integration2"."main_marts"."dim_order_status"
where status_key is not null
group by status_key
having count(*) > 1



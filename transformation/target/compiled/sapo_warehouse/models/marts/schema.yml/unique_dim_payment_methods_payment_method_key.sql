
    
    

select
    payment_method_key as unique_field,
    count(*) as n_records

from "data_integration2"."main_marts"."dim_payment_methods"
where payment_method_key is not null
group by payment_method_key
having count(*) > 1



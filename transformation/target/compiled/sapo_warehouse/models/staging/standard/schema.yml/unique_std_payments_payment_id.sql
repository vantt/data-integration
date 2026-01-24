
    
    

select
    payment_id as unique_field,
    count(*) as n_records

from "data_integration2"."main_staging"."std_payments"
where payment_id is not null
group by payment_id
having count(*) > 1



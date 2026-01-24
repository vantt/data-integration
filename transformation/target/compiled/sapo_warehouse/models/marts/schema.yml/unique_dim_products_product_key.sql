
    
    

select
    product_key as unique_field,
    count(*) as n_records

from "data_integration2"."main_marts"."dim_products"
where product_key is not null
group by product_key
having count(*) > 1



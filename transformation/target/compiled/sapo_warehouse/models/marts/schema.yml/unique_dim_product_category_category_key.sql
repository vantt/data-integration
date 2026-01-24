
    
    

select
    category_key as unique_field,
    count(*) as n_records

from "data_integration2"."main_marts"."dim_product_category"
where category_key is not null
group by category_key
having count(*) > 1



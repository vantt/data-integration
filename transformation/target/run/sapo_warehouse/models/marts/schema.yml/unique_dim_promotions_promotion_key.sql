
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    promotion_key as unique_field,
    count(*) as n_records

from "data_integration2"."main_marts"."dim_promotions"
where promotion_key is not null
group by promotion_key
having count(*) > 1



  
  
      
    ) dbt_internal_test
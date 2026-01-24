
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select promotion_key
from "data_integration2"."main_marts"."dim_promotions"
where promotion_key is null



  
  
      
    ) dbt_internal_test

    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select order_id
from "data_integration2"."main_marts"."fact_sales"
where order_id is null



  
  
      
    ) dbt_internal_test
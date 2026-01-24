
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select status_key
from "data_integration2"."main_marts"."dim_order_status"
where status_key is null



  
  
      
    ) dbt_internal_test
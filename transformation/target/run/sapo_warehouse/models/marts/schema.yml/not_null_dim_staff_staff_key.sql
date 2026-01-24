
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select staff_key
from "data_integration2"."main_marts"."dim_staff"
where staff_key is null



  
  
      
    ) dbt_internal_test
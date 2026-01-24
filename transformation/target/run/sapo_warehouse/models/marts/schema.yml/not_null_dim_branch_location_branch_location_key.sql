
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select branch_location_key
from "data_integration2"."main_marts"."dim_branch_location"
where branch_location_key is null



  
  
      
    ) dbt_internal_test
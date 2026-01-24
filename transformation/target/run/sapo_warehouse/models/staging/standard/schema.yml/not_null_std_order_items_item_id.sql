
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select item_id
from "data_integration2"."main_staging"."std_order_items"
where item_id is null



  
  
      
    ) dbt_internal_test
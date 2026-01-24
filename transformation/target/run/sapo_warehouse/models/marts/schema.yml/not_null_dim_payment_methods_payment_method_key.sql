
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select payment_method_key
from "data_integration2"."main_marts"."dim_payment_methods"
where payment_method_key is null



  
  
      
    ) dbt_internal_test
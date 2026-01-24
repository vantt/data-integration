
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        fulfillment_status as value_field,
        count(*) as n_records

    from "data_integration2"."main_staging"."std_orders"
    group by fulfillment_status

)

select *
from all_values
where value_field not in (
    'FULFILLED','UNFULFILLED','PARTIALLY_FULFILLED','RETURNED','SHIPPING'
)



  
  
      
    ) dbt_internal_test
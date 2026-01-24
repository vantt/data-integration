
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        status as value_field,
        count(*) as n_records

    from "data_integration2"."main_staging"."std_payments"
    group by status

)

select *
from all_values
where value_field not in (
    'SUCCESS','PENDING','FAILED','REFUNDED'
)



  
  
      
    ) dbt_internal_test

    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    fulfillment_id as unique_field,
    count(*) as n_records

from "data_integration2"."main_staging"."std_fulfillments"
where fulfillment_id is not null
group by fulfillment_id
having count(*) > 1



  
  
      
    ) dbt_internal_test
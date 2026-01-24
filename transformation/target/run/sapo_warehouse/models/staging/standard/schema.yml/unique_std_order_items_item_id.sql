
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    item_id as unique_field,
    count(*) as n_records

from "data_integration2"."main_staging"."std_order_items"
where item_id is not null
group by item_id
having count(*) > 1



  
  
      
    ) dbt_internal_test
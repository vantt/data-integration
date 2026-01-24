
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    staff_key as unique_field,
    count(*) as n_records

from "data_integration2"."main_marts"."dim_staff"
where staff_key is not null
group by staff_key
having count(*) > 1



  
  
      
    ) dbt_internal_test
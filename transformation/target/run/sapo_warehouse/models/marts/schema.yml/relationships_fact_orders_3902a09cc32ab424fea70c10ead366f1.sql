
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select branch_location_key as from_field
    from "data_integration2"."main_marts"."fact_orders"
    where branch_location_key is not null
),

parent as (
    select branch_location_key as to_field
    from "data_integration2"."main_marts"."dim_branch_location"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test
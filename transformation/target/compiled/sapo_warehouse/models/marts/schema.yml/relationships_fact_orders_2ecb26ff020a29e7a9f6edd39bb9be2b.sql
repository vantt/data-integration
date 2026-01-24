
    
    

with child as (
    select location_key as from_field
    from "data_integration2"."main_marts"."fact_orders"
    where location_key is not null
),

parent as (
    select location_key as to_field
    from "data_integration2"."main_marts"."dim_locations"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



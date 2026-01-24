
    
    

select
    branch_location_key as unique_field,
    count(*) as n_records

from "data_integration2"."main_marts"."dim_branch_location"
where branch_location_key is not null
group by branch_location_key
having count(*) > 1



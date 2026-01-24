
      create or replace view "data_integration2"."main_marts"."dim_staff__dbt_int" as (
        select * from read_parquet('D:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2\data_lake\export\marts\v_20260124_212222/dim_staff.parquet', union_by_name=False)
        -- if relation is empty, filter by all columns having null values
        
      );
    
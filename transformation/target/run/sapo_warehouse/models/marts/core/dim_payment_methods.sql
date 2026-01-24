
      create or replace view "data_integration2"."main_marts"."dim_payment_methods__dbt_int" as (
        select * from read_parquet('D:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2\data_lake\export\marts\v_20260125_010437/dim_payment_methods.parquet', union_by_name=False)
        -- if relation is empty, filter by all columns having null values
        
      );
    
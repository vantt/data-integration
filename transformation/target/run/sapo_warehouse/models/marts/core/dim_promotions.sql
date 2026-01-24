
      create or replace view "data_integration2"."main_marts"."dim_promotions__dbt_int" as (
        select * from read_parquet('D:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2\data_lake\export\marts\v_20260124_161825/dim_promotions.parquet', union_by_name=False)
        -- if relation is empty, filter by all columns having null values
        
          where 1 AND "promotion_key" is not NULL AND "promotion_code" is not NULL AND "discount_amount" is not NULL AND "promotion_type" is not NULL
      );
    
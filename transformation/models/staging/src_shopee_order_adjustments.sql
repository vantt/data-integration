{{ config(materialized='view', tags=['src', 'shopee']) }}

-- Shopee order adjustments (marketing fees, compensations, etc.)
-- Business key: (order_code, adjustment_completed_at, adjustment_type)
-- Note: explicit CAST to VARCHAR in PARTITION BY to avoid DuckDB internal bind error
-- with DATE columns from hive-partitioned parquet reads.

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_code, CAST(adjustment_completed_at AS VARCHAR), adjustment_type
            ORDER BY ingested_at DESC
        ) AS rn
    FROM {{ source('shopee_raw', 'order_adjustments') }}
)

SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1

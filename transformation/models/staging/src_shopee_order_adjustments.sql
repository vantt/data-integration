{{ config(materialized='view', tags=['src', 'shopee']) }}

-- Shopee order adjustments (marketing fees, compensations, etc.)
-- Dedup key: (order_code, adjustment_completed_at, adjustment_type, adjustment_amount).
-- amount is included so two legitimate same-day same-type adjustments with different
-- amounts are preserved; only exact-duplicate ingests collapse.
-- Note: explicit CAST to VARCHAR in PARTITION BY to avoid DuckDB internal bind error
-- with DATE columns from hive-partitioned parquet reads.
--
-- Safety placeholder: a sentinel parquet lives at year=1970/month=1/
-- shopee_income_safety_placeholder.parquet to guarantee the source glob never
-- matches zero files (prevents a cascading "No files found" failure when the
-- first real drop has no adjustment rows or in a fresh environment). The
-- sentinel row is filtered out below; it never reaches int_/fact_ layers.

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_code,
                         CAST(adjustment_completed_at AS VARCHAR),
                         adjustment_type,
                         adjustment_amount
            ORDER BY ingested_at DESC
        ) AS rn
    FROM {{ source('shopee_raw', 'order_adjustments') }}
)

SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1
  AND order_code <> '_safety_placeholder'

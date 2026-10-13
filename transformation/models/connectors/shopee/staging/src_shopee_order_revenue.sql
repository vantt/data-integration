{{ config(materialized='view', tags=['src', 'shopee']) }}

-- Dedup Shopee order-level revenue by order_code, keep latest ingested_at.
-- View materialization: file-drop sources are small (~100 rows), full-scan dedup is cheap.

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_code
            ORDER BY ingested_at DESC
        ) AS rn
    FROM {{ source('shopee_raw', 'order_revenue') }}
)

SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1

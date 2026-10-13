{{ config(materialized='view', tags=['src', 'shopee']) }}

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_code, product_code
            ORDER BY ingested_at DESC
        ) AS rn
    FROM {{ source('shopee_raw', 'order_revenue_items') }}
)

SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1

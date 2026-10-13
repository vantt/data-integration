{{ config(materialized='view', tags=['src', 'shopee']) }}

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY order_code
            ORDER BY ingested_at DESC
        ) AS rn
    FROM {{ source('shopee_raw', 'order_service_fees') }}
)

SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1

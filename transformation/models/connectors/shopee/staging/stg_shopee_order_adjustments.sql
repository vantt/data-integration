{{ config(materialized='view', tags=['stg', 'shopee']) }}

-- Shopee order adjustments: type casting + cleanup.

SELECT
    order_code,
    CAST(adjustment_completed_at AS DATE) AS adjustment_completed_at,
    adjustment_type,
    adjustment_reason,
    CAST(adjustment_amount AS BIGINT) AS adjustment_amount,
    CAST(payout_released_at AS DATE) AS payout_released_at,
    source_file,
    ingested_at
FROM {{ ref('src_shopee_order_adjustments') }}

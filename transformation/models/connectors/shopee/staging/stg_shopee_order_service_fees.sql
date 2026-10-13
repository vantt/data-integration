{{ config(materialized='view', tags=['stg', 'shopee']) }}

-- Shopee extra service fees: infrastructure + Xtra voucher.

SELECT
    order_code,
    CAST(infrastructure_fee AS BIGINT) AS infrastructure_fee,
    CAST(voucher_xtra_fee AS BIGINT)   AS voucher_xtra_fee,
    source_file,
    ingested_at
FROM {{ ref('src_shopee_order_service_fees') }}

{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    code,
    customer_id::INTEGER                        AS customer_id,
    token,
    campaign_id,
    min_order::BIGINT                           AS min_order_vnd,
    issued_at::TIMESTAMPTZ                      AS issued_at,
    redeemed_at::TIMESTAMPTZ                    AS redeemed_at,
    -- Explicit VARCHAR cast: DuckDB may infer DOUBLE from parquet when column is sparse/null.
    order_code::VARCHAR                         AS order_code,
    order_code IS NOT NULL                      AS is_redeemed
FROM {{ source('crm_export', 'crm_hug_voucher') }}
WHERE customer_id IS NOT NULL

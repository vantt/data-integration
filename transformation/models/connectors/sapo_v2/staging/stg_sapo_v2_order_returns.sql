{{ config(materialized='view', tags=['staging', 'sapo']) }}

SELECT
    order_return_id                           AS return_id,
    TRY_CAST(order_id   AS BIGINT)            AS order_id,
    order_code,
    return_status,
    refund_status,
    COALESCE(reason, note)                    AS return_reason,
    total_amount                              AS refund_amount,
    total_quantity                            AS return_quantity,
    TRY_CAST(issued_on   AS TIMESTAMPTZ)      AS issued_at,
    TRY_CAST(received_on AS TIMESTAMPTZ)      AS received_at,
    TRY_CAST(created_on  AS TIMESTAMPTZ)      AS created_at,
    TRY_CAST(modified_on AS TIMESTAMPTZ)      AS modified_at
FROM {{ ref('src_sapo_v2_order_returns') }}

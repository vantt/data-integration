{{ config(
    materialized='view',
    tags=['staging', 'payments']
) }}

-- =================================================================================================
-- STAGING: SAPO PAYMENTS
-- =================================================================================================
-- Purpose:
--   Unnest payments_json from src_sapo_orders into one row per payment transaction.
-- =================================================================================================

WITH raw_source AS (
    SELECT * FROM {{ ref('src_sapo_orders_v2') }}
),

unnested_payments AS (
    SELECT
        entity_id as order_entity_id,
        order_id,
        unnest(from_json(payments_json, '["JSON"]')) as payment_json,
        event_timestamp
    FROM raw_source
    WHERE payments_json IS NOT NULL
      AND payments_json NOT IN ('[]', 'null', '')
)

SELECT
    -- IDs
    json_extract_string(payment_json, '$.id') as payment_id,
    order_id,

    -- Method & Type
    json_extract_string(payment_json, '$.payment_method_id') as payment_method_id,
    json_extract_string(payment_json, '$.code') as payment_code,

    -- Financials (default 0 if amount is null/malformed)
    coalesce(try_cast(json_extract_string(payment_json, '$.amount') as DECIMAL(18,2)), 0.00) as amount,

    -- Status
    json_extract_string(payment_json, '$.status') as status,

    -- Reference
    json_extract_string(payment_json, '$.reference') as reference_code,

    -- Timestamps
    json_extract_string(payment_json, '$.created_on') as created_on,
    json_extract_string(payment_json, '$.paid_on') as paid_on,

    event_timestamp as source_timestamp

FROM unnested_payments

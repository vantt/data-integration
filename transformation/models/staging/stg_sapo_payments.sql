{{ config(
    materialized='view',
    tags=['staging', 'payments']
) }}

-- =================================================================================================
-- HOP 5: STAGING - SAPO PAYMENTS
-- =================================================================================================
-- Purpose:
-- 1. Unnest the `payments` array to track partial payments and multiple payment methods.
-- 2. Essential for reconciliation (e.g. Customer paid 30% via Bank, 70% COD).
--
-- Key Fields:
-- - `payment_method_id`: Maps to reference table (COD, Bank Transfer, QR).
-- - `amount`: Value of this specific transaction.
-- - `status`: 'paid', 'pending', 'refunded'.
-- =================================================================================================

WITH raw_source AS (
    SELECT * FROM {{ ref('src_sapo_orders') }}
),

unnested_payments AS (
    SELECT
        entity_id as order_entity_id,
        json_extract_string(payload, '$.id') as order_id,
        
        -- UNNEST payments array (Note: order payload has 'payments' field)
        unnest(from_json(json_extract_string(payload, '$.payments'), '["JSON"]')) as payment_json,
        
        unnest(from_json(json_extract_string(payload, '$.payments'), '["JSON"]')) as payment_json,
        
        event_timestamp
        
    FROM raw_source
    WHERE json_extract_string(payload, '$.payments') IS NOT NULL
)

SELECT
    -- IDs
    json_extract_string(payment_json, '$.id') as payment_id,
    order_id,
    
    -- Method & Type
    json_extract_string(payment_json, '$.payment_method_id') as payment_method_id,
    json_extract_string(payment_json, '$.code') as payment_code, -- if exists
    
    -- Financials
    try_cast(json_extract_string(payment_json, '$.amount') as DECIMAL(18,2)) as amount,
    
    -- Status
    json_extract_string(payment_json, '$.status') as status,
    
    -- Reference
    json_extract_string(payment_json, '$.reference') as reference_code,
    
    -- Timestamps
    json_extract_string(payment_json, '$.created_on') as created_on,
    json_extract_string(payment_json, '$.paid_on') as paid_on,

    json_extract_string(payment_json, '$.paid_on') as paid_on,
    
    event_timestamp as source_timestamp

FROM unnested_payments

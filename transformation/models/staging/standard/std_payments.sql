{{ config(
    materialized='view',
    tags=['standard', 'payments']
) }}

-- =================================================================================================
-- HOP 5: STANDARD PAYMENTS
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_payments_v2') }}
)

SELECT
    -- Identity
    payment_id,
    order_id,
    
    -- Payment Details
    payment_method_id, -- Keep ID or join with ref table for name
    'CASH' as payment_method_type, -- Placeholder; ideally map payment_method_id to Type
    
    amount,
    
    -- Status
    CASE
        WHEN status = 'paid' THEN 'SUCCESS'
        WHEN status = 'pending' THEN 'PENDING'
        WHEN status = 'voided' THEN 'FAILED'
        WHEN status = 'refunded' THEN 'REFUNDED'
        ELSE 'PENDING'
    END as status,
    
    reference_code,
    
    -- Timestamps
    try_cast(created_on as TIMESTAMPTZ) as created_at,
    try_cast(paid_on as TIMESTAMPTZ) as paid_at,
    
    source_timestamp as extracted_at,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo' as source_system,
    'v2'   as source_version

FROM source_data

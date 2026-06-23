{{ config(
    materialized='view',
    tags=['standard', 'payments']
) }}

-- =================================================================================================
-- HOP 5: STANDARD PAYMENTS
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_v2_payments') }}
),

payment_method_ref AS (
    SELECT
        cast(id as varchar) as payment_method_id,
        type               as payment_method_type
    FROM {{ ref('ref_payment_methods') }}
)

SELECT
    -- Identity
    payment_id,
    order_id,

    -- Payment Details
    s.payment_method_id,
    -- Map payment_method_id → type via ref_payment_methods seed (cod/cash/transfer/etc.)
    -- Falls back to 'unknown' when id not in seed (new method not yet catalogued)
    COALESCE(pm.payment_method_type, 'unknown') as payment_method_type,

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
    'sapo_v2' as source_system,
    'v2'   as source_version

FROM source_data s
LEFT JOIN payment_method_ref pm ON s.payment_method_id = pm.payment_method_id

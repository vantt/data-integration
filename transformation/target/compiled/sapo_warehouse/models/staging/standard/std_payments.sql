

-- =================================================================================================
-- HOP 5: STANDARD PAYMENTS
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM "data_integration2"."main_staging"."stg_sapo_payments"
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
    try_cast(created_on as TIMESTAMP) as created_at,
    try_cast(paid_on as TIMESTAMP) as paid_at,
    
    source_timestamp as extracted_at

FROM source_data
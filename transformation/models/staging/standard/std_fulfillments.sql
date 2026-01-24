{{ config(
    materialized='view',
    tags=['standard', 'fulfillments']
) }}

-- =================================================================================================
-- HOP 5: STANDARD FULFILLMENTS
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_fulfillments') }}
)

SELECT
    -- Identity
    fulfillment_id,
    order_id,
    fulfillment_code,
    
    -- Status
    CASE
        WHEN status = 'success' THEN 'DELIVERED' -- Map Sapo success to DELIVERED
        WHEN status = 'shipping' THEN 'SHIPPING'
        WHEN status = 'packed' THEN 'PACKED'
        WHEN status = 'cancelled' THEN 'CANCELLED'
        WHEN status = 'error' THEN 'FAILED'
        ELSE 'PENDING'
    END as status,
    
    -- Tracking
    tracking_code,
    carrier_id,
    shipping_service,
    cod_amount,
    
    -- Timestamps
    try_cast(created_on as TIMESTAMP) as created_at,
    try_cast(shipped_on as TIMESTAMP) as shipped_at,
    -- delivered_at could be mapped from modified_on if status is success
    
    source_timestamp as extracted_at

FROM source_data

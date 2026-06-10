{{ config(
    materialized='view',
    tags=['standard', 'fulfillments']
) }}

-- =================================================================================================
-- HOP 5: STANDARD FULFILLMENTS
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_fulfillments_v2') }}
)

SELECT
    -- Identity
    fulfillment_id,
    order_id,
    fulfillment_code,
    
    -- Status (Sapo fulfillment status values: received/fulfilled/packed/cancelled)
    CASE
        WHEN status = 'received'  THEN 'DELIVERED'
        WHEN status = 'fulfilled' THEN 'SHIPPING'
        WHEN status = 'packed'    THEN 'PACKED'
        WHEN status = 'cancelled' THEN 'CANCELLED'
        WHEN status = 'error'     THEN 'FAILED'
        ELSE 'PENDING'
    END as status,
    shipment_status,

    -- Tracking
    tracking_code,
    carrier_id,
    shipping_service,
    cod_amount,

    -- Timestamps
    try_cast(created_on as TIMESTAMPTZ) as created_at,
    try_cast(shipped_on as TIMESTAMPTZ) as shipped_at,
    CASE WHEN status = 'received'
         THEN try_cast(modified_on as TIMESTAMPTZ)
    END as delivered_at,

    source_timestamp as extracted_at,

    -- Source lineage (P0 gate discriminator; v3 union sets 'v3')
    'sapo' as source_system,
    'v2'   as source_version

FROM source_data

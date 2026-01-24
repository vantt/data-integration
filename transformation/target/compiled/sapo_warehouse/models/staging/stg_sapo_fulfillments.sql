

-- =================================================================================================
-- HOP 5: STAGING - SAPO FULFILLMENTS
-- =================================================================================================
-- Purpose:
-- 1. Unnest the `fulfillments` array to track individual shipments.
-- 2. Critical for tracking split shipments and delivery status from 3PLs (GHTK, GHN).
--
-- Key Fields:
-- - `tracking_code`: Used for external lookup.
-- - `carrier_id` / `shipping_service`: Logistics provider info.
-- - `status`: Sapo-specific status (e.g. 'packed', 'shipping', 'success').
-- =================================================================================================

WITH raw_source AS (
    SELECT * FROM "data_integration2"."main_staging"."src_sapo_orders"
),

unnested_fulfillments AS (
    SELECT
        entity_id as order_entity_id,
        json_extract_string(payload, '$.id') as order_id,
        
        -- UNNEST fulfillments array
        unnest(from_json(json_extract_string(payload, '$.fulfillments'), '["JSON"]')) as fulfillment_json,
        
        unnest(from_json(json_extract_string(payload, '$.fulfillments'), '["JSON"]')) as fulfillment_json,
        
        event_timestamp
        
    FROM raw_source
    WHERE json_extract_string(payload, '$.fulfillments') IS NOT NULL
)

SELECT
    -- IDs
    json_extract_string(fulfillment_json, '$.id') as fulfillment_id,
    order_id,
    
    -- Codes & Tracking
    json_extract_string(fulfillment_json, '$.code') as fulfillment_code,
    json_extract_string(fulfillment_json, '$.shipment.tracking_code') as tracking_code,
    json_extract_string(fulfillment_json, '$.shipment.delivery_service_provider_id') as carrier_id,
    json_extract_string(fulfillment_json, '$.shipment.service_name') as shipping_service,
    
    -- Status
    json_extract_string(fulfillment_json, '$.status') as status,
    json_extract_string(fulfillment_json, '$.shipment.status') as shipment_status,
    
    -- Amounts
    try_cast(json_extract_string(fulfillment_json, '$.shipment.cod_amount') as DECIMAL(18,2)) as cod_amount,
    
    -- Timestamps
    json_extract_string(fulfillment_json, '$.created_on') as created_on,
    json_extract_string(fulfillment_json, '$.shipped_on') as shipped_on,
    json_extract_string(fulfillment_json, '$.shipment.modified_on') as modified_on,
    
    json_extract_string(fulfillment_json, '$.shipment.modified_on') as modified_on,
    
    event_timestamp as source_timestamp

FROM unnested_fulfillments
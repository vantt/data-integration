{{ config(
    materialized='view',
    tags=['staging', 'fulfillments']
) }}

-- =================================================================================================
-- STAGING: SAPO FULFILLMENTS
-- =================================================================================================
-- Purpose:
--   Unnest fulfillments_json from src_sapo_orders into one row per shipment.
-- =================================================================================================

WITH raw_source AS (
    SELECT * FROM {{ ref('src_sapo_v2_orders') }}
),

unnested_fulfillments AS (
    SELECT
        entity_id as order_entity_id,
        order_id,
        unnest(from_json(fulfillments_json, '["JSON"]')) as fulfillment_json,
        event_timestamp
    FROM raw_source
    WHERE fulfillments_json IS NOT NULL
      AND fulfillments_json NOT IN ('[]', 'null', '')
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

    event_timestamp as source_timestamp

FROM unnested_fulfillments

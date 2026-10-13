{{ config(
    materialized='view',
    tags=['standard', 'orders']
) }}

-- Standard order history events (status/payment/fulfillment snapshots with previous values): thin pass-through over int_order_snapshots_ranked.
-- Grain: 1/(order_id, snapshot_seq).
-- Same columns, types and order as the source, plus source_system at the end.
-- Core models read this instead of the connector model (std gate R1).

WITH source_data AS (
    SELECT * FROM {{ ref('int_order_snapshots_ranked') }}
)

SELECT
    order_id,
    event_type,
    event_timestamp,
    actor_name,
    original_event_id,
    status,
    payment_status,
    fulfillment_status,
    cancelled_on,
    completed_on,
    finalized_on,
    snapshot_seq,
    prev_status,
    prev_payment_status,
    prev_fulfillment_status,
    'sapo_v2' AS source_system
FROM source_data

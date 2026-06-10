{{ config(materialized='view', tags=['intermediate', 'sapo', 'history_log']) }}

WITH deduped AS (
    -- Dedup same Sapo event_id ingested across multiple pipeline runs (min_overlap_items reprocessing)
    SELECT
        entity_id,
        event_type,
        event_timestamp::TIMESTAMPTZ                                 AS event_timestamp,
        sync_metadata->>'actor_name'                                 AS actor_name,
        sync_metadata->>'original_event_id'                         AS original_event_id,
        payload->>'status'                                           AS status,
        payload->>'payment_status'                                   AS payment_status,
        payload->>'fulfillment_status'                               AS fulfillment_status,
        payload->>'cancelled_on'                                     AS cancelled_on,
        payload->>'completed_on'                                     AS completed_on,
        payload->>'finalized_on'                                     AS finalized_on,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id, sync_metadata->>'original_event_id'
            ORDER BY event_timestamp
        )                                                            AS _dedup_rn
    FROM {{ source('sapo_v2_raw', 'order') }}
    WHERE ingest_method = 'history_log'
),

ranked AS (
    SELECT
        entity_id                                                    AS order_id,
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
        ROW_NUMBER() OVER (
            PARTITION BY entity_id ORDER BY event_timestamp
        )                                                            AS snapshot_seq,
        LAG(status) OVER (
            PARTITION BY entity_id ORDER BY event_timestamp
        )                                                            AS prev_status,
        LAG(payment_status) OVER (
            PARTITION BY entity_id ORDER BY event_timestamp
        )                                                            AS prev_payment_status,
        LAG(fulfillment_status) OVER (
            PARTITION BY entity_id ORDER BY event_timestamp
        )                                                            AS prev_fulfillment_status
    FROM deduped
    WHERE _dedup_rn = 1
)

SELECT * FROM ranked

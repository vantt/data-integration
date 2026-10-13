{{ config(
    tags=['mart', 'sapo', 'history_log'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

WITH transitions AS (
    SELECT
        t.order_id,
        o.order_code,
        t.snapshot_seq,
        t.event_timestamp,
        t.event_type,
        t.actor_name,
        t.original_event_id,
        t.status,
        t.payment_status,
        t.fulfillment_status,
        t.cancelled_on,
        t.completed_on,
        t.finalized_on,
        t.prev_status,
        t.prev_payment_status,
        t.prev_fulfillment_status,
        CASE
            WHEN t.snapshot_seq = 1                                                 THEN 'created'
            WHEN t.status = 'cancelled' AND t.prev_status != 'cancelled'            THEN 'cancelled'
            WHEN t.status = 'completed' AND COALESCE(t.prev_status,'') != 'completed' THEN 'completed'
            WHEN t.fulfillment_status = 'shipped'
                 AND COALESCE(t.prev_fulfillment_status,'') != 'shipped'            THEN 'shipped'
            WHEN t.payment_status = 'paid'
                 AND COALESCE(t.prev_payment_status,'') != 'paid'                   THEN 'payment_received'
            WHEN t.status != COALESCE(t.prev_status,'')
                 OR t.payment_status != COALESCE(t.prev_payment_status,'')
                 OR t.fulfillment_status != COALESCE(t.prev_fulfillment_status,'')  THEN 'updated'
            ELSE NULL
        END AS transition_type,
        CASE
            WHEN t.snapshot_seq = 1 THEN NULL
            ELSE ROUND(
                EXTRACT(EPOCH FROM (
                    t.event_timestamp - LAG(t.event_timestamp) OVER (
                        PARTITION BY t.order_id ORDER BY t.snapshot_seq
                    )
                )) / 86400.0, 2
            )
        END AS days_since_prev_event
    FROM {{ ref('int_order_snapshots_ranked') }} t
    LEFT JOIN {{ ref('stg_sapo_v2_orders') }} o ON t.order_id = o.order_id
)
SELECT *
FROM transitions
WHERE transition_type IS NOT NULL

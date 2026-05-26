{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Per-return fact: one row per Sapo return event.
-- Returns are recognized at return date — original order P&L is not restated.
-- channel_key inherited from the originating order.

WITH returns AS (
    SELECT * FROM {{ ref('stg_sapo_order_returns') }}
),

order_channels AS (
    SELECT order_code, channel_key
    FROM {{ ref('fact_orders') }}
)

SELECT
    r.return_id,
    r.order_id,
    r.order_code,
    COALESCE(r.issued_at, r.created_at)                                       AS return_timestamp,
    DATE(COALESCE(r.issued_at, r.created_at))                                 AS return_date,
    r.refund_amount,
    r.return_quantity,
    r.return_status,
    r.refund_status,
    r.return_reason,
    oc.channel_key,
    COALESCE(
        CAST(STRFTIME(COALESCE(r.issued_at, r.created_at), '%Y%m%d') AS INTEGER),
        19000101
    )                                                                         AS date_key
FROM returns r
LEFT JOIN order_channels oc ON r.order_code = oc.order_code

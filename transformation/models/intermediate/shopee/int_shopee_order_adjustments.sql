{{ config(
    tags=['int', 'shopee'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Shopee per-order adjustments (marketing fees, compensations, etc.)
-- One row per adjustment per order. Standalone table — join to int_shopee_order_fees via order_code.

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'order_code', 'adjustment_completed_at', 'adjustment_type'
    ]) }} AS shopee_order_adjustment_sk,
    order_code,
    adjustment_completed_at,
    adjustment_type,
    adjustment_reason,
    adjustment_amount,
    payout_released_at,
    source_file,
    ingested_at
FROM {{ ref('stg_shopee_order_adjustments') }}

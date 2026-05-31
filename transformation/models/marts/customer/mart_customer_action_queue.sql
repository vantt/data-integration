{{ config(
    tags=['mart', 'customer'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Customer action queue: one actionable row per RETAIL customer needing outreach.
-- Automatically discovered as a serving view by sapo_serving_db Dagster asset.
-- action_type drives the detailView Actions tab and CS/Sales daily workflow.

WITH customers AS (
    SELECT
        customer_key,
        customer_id,
        customer_code,
        full_name,
        phone,
        email,
        value_group,
        customer_status,
        next_purchase_signal,
        discount_sensitivity,
        lifetime_value,
        total_orders_count,
        avg_order_value,
        avg_days_between_orders,
        cancel_rate,
        recency_days,
        last_order_date,
        predicted_next_purchase_date,
        channel_preference,
        product_affinity,
        payment_behavior
    FROM {{ ref('dim_customers') }}
    WHERE customer_type = 'RETAIL'
      AND customer_id != 'Unknown'
      AND total_orders_count > 0
),

classified AS (
    SELECT
        *,
        CASE
            WHEN value_group IN ('VALUE_VIP', 'VALUE_GOLD') AND customer_status = 'At Risk'
                THEN 'CALL_NOW'
            WHEN value_group IN ('VALUE_VIP', 'VALUE_GOLD') AND next_purchase_signal = 'OVERDUE'
                THEN 'REORDER_NUDGE'
            WHEN value_group IN ('VALUE_VIP', 'VALUE_GOLD') AND customer_status = 'Churned'
                THEN 'WIN_BACK'
            WHEN value_group = 'VALUE_SILVER' AND next_purchase_signal = 'OVERDUE'
                THEN 'REORDER_NUDGE'
            WHEN value_group = 'VALUE_SILVER' AND customer_status = 'Churned'
                THEN 'WIN_BACK'
            WHEN total_orders_count = 1 AND recency_days BETWEEN 15 AND 45
                THEN 'SECOND_ORDER'
            WHEN cancel_rate > 0.5 AND total_orders_count >= 3
                THEN 'HIGH_CANCEL_RISK'
            ELSE NULL
        END AS action_type
    FROM customers
)

SELECT
    customer_key,
    customer_id,
    customer_code,
    full_name,
    phone,
    email,
    value_group,
    customer_status,
    next_purchase_signal,
    discount_sensitivity,
    lifetime_value,
    total_orders_count,
    avg_order_value,
    avg_days_between_orders,
    cancel_rate,
    recency_days,
    last_order_date,
    predicted_next_purchase_date,
    channel_preference,
    product_affinity,
    payment_behavior,
    action_type,
    CASE action_type
        WHEN 'CALL_NOW'         THEN 1
        WHEN 'REORDER_NUDGE'    THEN 2
        WHEN 'WIN_BACK'         THEN 3
        WHEN 'SECOND_ORDER'     THEN 4
        WHEN 'HIGH_CANCEL_RISK' THEN 5
        ELSE 9
    END AS priority_rank,
    CASE action_type
        WHEN 'CALL_NOW'
            THEN 'VIP/Gold chưa mua ' || recency_days || ' ngày — gọi điện ngay'
        WHEN 'REORDER_NUDGE'
            THEN 'Quá hạn tái mua ' || (recency_days - COALESCE(avg_days_between_orders, recency_days)) || ' ngày — nhắn nhở'
        WHEN 'WIN_BACK'
            THEN 'Mất ' || recency_days || ' ngày — cần offer win-back'
        WHEN 'SECOND_ORDER'
            THEN 'Mua 1 lần ' || recency_days || ' ngày trước — push đơn 2'
        WHEN 'HIGH_CANCEL_RISK'
            THEN 'Tỷ lệ huỷ ' || ROUND(cancel_rate * 100)::INTEGER || '% — cần xác nhận'
        ELSE NULL
    END AS action_rationale,
    CASE action_type
        WHEN 'CALL_NOW'      THEN ROUND(COALESCE(avg_order_value, 0) * 2)::BIGINT
        WHEN 'REORDER_NUDGE' THEN ROUND(COALESCE(avg_order_value, 0))::BIGINT
        WHEN 'WIN_BACK'      THEN ROUND(COALESCE(avg_order_value, 0) * 3)::BIGINT
        WHEN 'SECOND_ORDER'  THEN ROUND(COALESCE(avg_order_value, 0))::BIGINT
        ELSE NULL
    END AS value_at_stake,
    current_timestamp AS queue_generated_at

FROM classified
WHERE action_type IS NOT NULL
ORDER BY priority_rank, lifetime_value DESC

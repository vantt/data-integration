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
        order_count,
        avg_order_spend,
        avg_days_between_orders,
        cancel_rate,
        recency_days,
        last_order_date,
        predicted_next_purchase_date,
        channel_preference,
        product_affinity,
        payment_behavior,
        lifetime_contribution_margin,
        is_margin_negative,
        -- Contactable = has a usable phone (no Zalo OA fallback exists). Drives CS/Sales reachability.
        (phone IS NOT NULL AND phone <> '') AS is_contactable
    FROM {{ ref('dim_customers') }}
    WHERE customer_type = 'RETAIL'
      AND customer_id != 'Unknown'
      AND order_count > 0
),

classified AS (
    SELECT
        *,
        -- High-value tiers (VIP/GOLD/SILVER). BRONZE excluded by design: low/negative
        -- contribution margin — not worth high-touch outreach (see is_margin_negative gate).
        CASE
            -- Đang nguội (At Risk) → gọi tay ngay
            WHEN value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER') AND customer_status = 'At Risk'
                THEN 'CALL_NOW'
            -- Quá hạn nhịp mua → nhắc tái mua
            WHEN value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER') AND next_purchase_signal = 'OVERDUE'
                THEN 'REORDER_NUDGE'
            -- Sắp tới hạn nhịp mua → nhắc TRƯỚC khi khách quên (giữ on-track)
            WHEN value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER') AND next_purchase_signal = 'DUE_SOON'
                THEN 'REORDER_PREEMPT'
            -- Đã churn → cần offer win-back
            WHEN value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER') AND customer_status = 'Churned'
                THEN 'WIN_BACK'
            WHEN order_count = 1 AND recency_days BETWEEN 15 AND 45
                THEN 'SECOND_ORDER'
            WHEN cancel_rate > 0.5 AND order_count >= 3
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
    order_count,
    avg_order_spend,
    avg_days_between_orders,
    cancel_rate,
    recency_days,
    last_order_date,
    predicted_next_purchase_date,
    channel_preference,
    product_affinity,
    payment_behavior,
    is_contactable,
    lifetime_contribution_margin,
    is_margin_negative,
    action_type,
    CASE action_type
        WHEN 'CALL_NOW'         THEN 1
        WHEN 'REORDER_NUDGE'    THEN 2
        WHEN 'REORDER_PREEMPT'  THEN 3
        WHEN 'WIN_BACK'         THEN 4
        WHEN 'SECOND_ORDER'     THEN 5
        WHEN 'HIGH_CANCEL_RISK' THEN 6
        ELSE 9
    END AS priority_rank,
    CASE action_type
        WHEN 'CALL_NOW'
            THEN 'VIP/Gold chưa mua ' || recency_days || ' ngày — gọi điện ngay'
        WHEN 'REORDER_NUDGE'
            THEN 'Quá hạn tái mua ' || (recency_days - COALESCE(avg_days_between_orders, recency_days)) || ' ngày — nhắn nhở'
        WHEN 'REORDER_PREEMPT'
            THEN 'Sắp tới hạn mua (~' || COALESCE(avg_days_between_orders, recency_days) || ' ngày/lần) — nhắc trước khi quên'
        WHEN 'WIN_BACK'
            THEN 'Mất ' || recency_days || ' ngày — cần offer win-back'
        WHEN 'SECOND_ORDER'
            THEN 'Mua 1 lần ' || recency_days || ' ngày trước — push đơn 2'
        WHEN 'HIGH_CANCEL_RISK'
            THEN 'Tỷ lệ huỷ ' || ROUND(cancel_rate * 100)::INTEGER || '% — cần xác nhận'
        ELSE NULL
    END AS action_rationale,
    CASE action_type
        WHEN 'CALL_NOW'      THEN ROUND(COALESCE(avg_order_spend, 0) * 2)::BIGINT
        WHEN 'REORDER_NUDGE' THEN ROUND(COALESCE(avg_order_spend, 0))::BIGINT
        WHEN 'REORDER_PREEMPT' THEN ROUND(COALESCE(avg_order_spend, 0))::BIGINT
        WHEN 'WIN_BACK'      THEN ROUND(COALESCE(avg_order_spend, 0) * 3)::BIGINT
        WHEN 'SECOND_ORDER'  THEN ROUND(COALESCE(avg_order_spend, 0))::BIGINT
        ELSE NULL
    END AS value_at_stake,
    current_timestamp AS queue_generated_at

FROM classified
WHERE action_type IS NOT NULL
ORDER BY priority_rank, lifetime_value DESC

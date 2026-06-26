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
        last_purchased_product,
        last_purchased_sku,
        top_affinity_product,
        top_affinity_sku,
        second_affinity_product,
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
),

last_contact AS (
    SELECT * FROM {{ ref('stg_crm__last_contact') }}
)

SELECT
    classified.customer_key,
    classified.customer_id,
    classified.customer_code,
    classified.full_name,
    classified.phone,
    classified.email,
    classified.value_group,
    classified.customer_status,
    classified.next_purchase_signal,
    classified.discount_sensitivity,
    classified.lifetime_value,
    classified.order_count,
    classified.avg_order_spend,
    classified.avg_days_between_orders,
    classified.cancel_rate,
    classified.recency_days,
    classified.last_order_date,
    classified.predicted_next_purchase_date,
    classified.channel_preference,
    classified.product_affinity,
    classified.last_purchased_product,
    classified.last_purchased_sku,
    classified.top_affinity_product,
    classified.top_affinity_sku,
    classified.second_affinity_product,
    classified.payment_behavior,
    classified.is_contactable,
    classified.lifetime_contribution_margin,
    classified.is_margin_negative,
    classified.action_type,
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
    current_timestamp AS queue_generated_at,
    lc.last_contacted_at,
    lc.last_contact_result,
    lc.last_contact_channel,
    CASE
        WHEN lc.last_contact_result IN ('answered', 'replied', 'met')
         AND lc.last_contacted_at >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
        THEN TRUE ELSE FALSE
    END                                                AS is_recently_contacted_positively

FROM classified
LEFT JOIN last_contact lc ON classified.customer_id::INTEGER = lc.customer_id
WHERE action_type IS NOT NULL
ORDER BY priority_rank, lifetime_value DESC

{{ config(
    tags=['mart', 'customer'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: CUSTOMER × SKU ACTION QUEUE
-- =============================================================================
-- Grain: (customer_key, sku) — one actionable row per customer per core SKU.
-- One customer can have multiple rows (one per SKU needing action today).
--
-- ACTION TYPES (priority order):
--   REORDER_OVERDUE  — supply ran out >7 days ago, customer is off regimen
--   REORDER_NUDGE    — supply just ran out or expires today
--   REORDER_PREEMPT  — supply expires within remind_lead_days; order now
--   PROGRESS_CHECK   — D12-16 journey: check in on customer experience
--   USAGE_FOLLOWUP   — D5-9 journey: confirm usage started, reinforce routine
--   GIFT_TO_PURCHASE — gift_only stream (Phase 4): gifted, never bought, 14-45d
--                      since gift received. Ships enabled=false in
--                      seed_action_scenario_registry (timing rule not yet reviewed).
--
-- Registry (seed_action_scenario_registry) controls enable/disable per action_type
-- at the output layer — see final WHERE/LEFT JOIN below.
--
-- SOURCE: int_customer_sku_supply_tracking (supply + stacking already computed)
-- Companion to mart_customer_action_queue (customer-level signals).
-- =============================================================================

-- last_order_code / last_sku_discount_rate / last_net_unit_price are now computed in
-- int_customer_sku_supply_tracking (same grain as last_purchase_date) to avoid desync.

WITH supply AS (
    SELECT * FROM {{ ref('int_customer_sku_supply_tracking') }}
),

customers AS (
    SELECT
        customer_key,
        customer_id,
        customer_code,
        full_name,
        phone,
        email,
        value_group,
        customer_status,
        lifetime_value,
        order_count,
        avg_order_spend
    FROM {{ ref('dim_customers') }}
    WHERE customer_type = 'RETAIL'
      AND customer_id   != 'Unknown'
      AND NOT is_us_gift_recipient   -- excludes RETAIL-tagged US gift-fulfilment recipients (Phase 4, dim_customers.sql:300-306)
),

-- Strategic tier + contactability (Phase 4). dim_customers.is_contactable is the
-- canonical source (mart_customer_tier.is_contactable is a passthrough of it) —
-- but it's stricter than the old local phone-presence check below: it excludes
-- masked/obfuscated marketplace-relay phones. Intentional semantic tightening,
-- not a no-op dedup. See mart_customer_tier.sql:11,28,74.
tier AS (
    SELECT customer_key, strategic_tier, is_contactable, tier_reason
    FROM {{ ref('mart_customer_tier') }}
),

last_contact AS (
    SELECT * FROM {{ ref('stg_crm__last_contact') }}
),

-- Compute day-based signals and classify action type
classified AS (
    SELECT
        s.*,
        cu.customer_id,
        cu.customer_code,
        cu.full_name,
        cu.phone,
        cu.email,
        cu.value_group,
        cu.customer_status,
        cu.lifetime_value,
        cu.order_count,
        cu.avg_order_spend,
        t.is_contactable,
        t.strategic_tier,

        DATE_DIFF('day', CURRENT_DATE, s.estimated_depletion_date) AS days_until_depletion,
        DATE_DIFF('day', s.last_purchase_date, CURRENT_DATE)       AS days_since_order,

        -- Priority cascade: GIFT_TO_PURCHASE (gift_only stream, Phase 4) checked first,
        -- then the unchanged purchased-stream cascade — journey touchpoints checked
        -- first (day-of-purchase window), then reorder urgency signals based on
        -- depletion date. The purchased-stream branch logic itself is untouched.
        CASE
            WHEN s.supply_stream = 'gift_only'
                 AND DATE_DIFF('day', s.last_purchase_date, CURRENT_DATE) BETWEEN 14 AND 45
                THEN 'GIFT_TO_PURCHASE'
            WHEN s.supply_stream = 'purchased' THEN
                CASE
                    WHEN s.journey_enabled AND DATE_DIFF('day', s.last_purchase_date, CURRENT_DATE) BETWEEN 5  AND 9
                        THEN 'USAGE_FOLLOWUP'
                    WHEN s.journey_enabled AND DATE_DIFF('day', s.last_purchase_date, CURRENT_DATE) BETWEEN 12 AND 16
                        THEN 'PROGRESS_CHECK'
                    WHEN DATE_DIFF('day', CURRENT_DATE, s.estimated_depletion_date) < -7
                        THEN 'REORDER_OVERDUE'
                    WHEN DATE_DIFF('day', CURRENT_DATE, s.estimated_depletion_date) BETWEEN -7 AND 0
                        THEN 'REORDER_NUDGE'
                    WHEN DATE_DIFF('day', CURRENT_DATE, s.estimated_depletion_date) BETWEEN 1 AND s.remind_lead_days
                        THEN 'REORDER_PREEMPT'
                    ELSE NULL
                END
            ELSE NULL
        END AS action_type

    FROM supply s
    JOIN customers cu ON s.customer_key = cu.customer_key
    LEFT JOIN tier t ON s.customer_key = t.customer_key
)

SELECT
    -- Customer keys
    classified.customer_key,
    classified.customer_id::INTEGER AS customer_id,
    classified.customer_code,
    classified.full_name,
    classified.phone,
    classified.email,
    classified.value_group,
    classified.customer_status,
    classified.lifetime_value,
    classified.order_count,
    classified.avg_order_spend,
    classified.is_contactable,
    classified.strategic_tier,

    -- SKU supply context
    classified.sku,
    classified.supply_stream,
    classified.product_group,
    classified.display_name          AS product_display_name,
    classified.last_purchase_date,
    classified.last_order_qty,
    classified.effective_supply_days,
    classified.estimated_depletion_date,
    classified.days_until_depletion,
    classified.days_since_order,
    classified.supply_days_per_unit,
    classified.dose_reduction_buffer,
    classified.remind_lead_days,

    -- Action
    classified.action_type,

    CASE classified.action_type
        WHEN 'REORDER_OVERDUE'  THEN 2
        WHEN 'REORDER_NUDGE'    THEN 3
        WHEN 'REORDER_PREEMPT'  THEN 5
        WHEN 'PROGRESS_CHECK'   THEN 6
        WHEN 'USAGE_FOLLOWUP'   THEN 7
        ELSE 9
    END AS priority_rank,

    CASE classified.action_type
        WHEN 'USAGE_FOLLOWUP'
            THEN 'Ngày ' || classified.days_since_order
                || ' dùng ' || classified.display_name
                || ' — hỏi thăm, nhắc dùng đúng liều'
        WHEN 'PROGRESS_CHECK'
            THEN 'Ngày ' || classified.days_since_order
                || ' dùng ' || classified.display_name
                || ' — hỏi cảm nhận, cần tư vấn gì không'
        WHEN 'REORDER_OVERDUE'
            THEN classified.display_name
                || ' hết ' || ABS(classified.days_until_depletion)
                || ' ngày — đứt liệu trình, cần mua lại ngay'
        WHEN 'REORDER_NUDGE'
            THEN classified.display_name
                || ' hết hôm nay hoặc vừa hết — nhắc mua thêm ngay'
        WHEN 'REORDER_PREEMPT'
            THEN classified.display_name
                || ' còn ' || classified.days_until_depletion
                || ' ngày — đặt trước để không đứt liệu trình'
        WHEN 'GIFT_TO_PURCHASE'
            THEN 'Được tặng ' || classified.display_name
                || ' ' || classified.days_since_order
                || ' ngày trước, chưa từng mua — hỏi cảm nhận, gợi ý mua chính'
        ELSE NULL
    END AS action_rationale,

    -- Last purchase context (for CS display: order · date · price · discount)
    classified.last_order_code,
    classified.last_sku_discount_rate,
    classified.last_net_unit_price,

    -- Last CRM contact context
    lc.last_contacted_at,
    lc.last_contact_result,
    lc.last_contact_channel,
    CASE
        WHEN lc.last_contact_result IN ('answered', 'replied', 'met')
         AND lc.last_contacted_at >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
        THEN TRUE ELSE FALSE
    END AS is_recently_contacted_positively,

    current_timestamp AS queue_generated_at

FROM classified
LEFT JOIN last_contact lc
    ON classified.customer_id::INTEGER = lc.customer_id
LEFT JOIN {{ ref('seed_action_scenario_registry') }} reg
    ON classified.action_type = reg.action_type
   AND reg.mart = 'mart_customer_sku_action_queue'
WHERE classified.action_type IS NOT NULL
  AND COALESCE(reg.enabled, TRUE) = TRUE   -- default TRUE if action_type missing from registry (safety net)
ORDER BY priority_rank, classified.lifetime_value DESC NULLS LAST

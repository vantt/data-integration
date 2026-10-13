{{ config(
    tags=['mart', 'customer'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Customer strategic tier: exactly ONE tier per customer (first-match decision tree).
-- Single source of truth for "which strategic track a customer belongs to" — consumed by
-- the re-sell funnel (identity-capture, second-order, win-back) and the Hug touchpoint platform.
-- Full recompute from dim_customers each run. Thresholds: activation window 90d, dead 365d.
-- 'real' = usable phone; 'masked' = NULL/empty/obfuscated(*) phone (marketplace relay).

WITH base AS (
    SELECT
        customer_key,
        customer_id,
        customer_code,
        full_name,
        customer_type,
        value_group,
        customer_status,
        order_count,
        recency_days,
        last_order_date,
        lifetime_value,
        lifetime_contribution_margin,
        channel_preference,
        is_contactable,
        source_contact_quality,
        contact_quality
    FROM {{ ref('dim_customers') }}
),

tiered AS (
    SELECT
        *,
        CASE
            -- Tạo nhưng chưa mua (lead sàn / huỷ) — giữ riêng để nuôi sau
            WHEN order_count = 0 THEN 'NONBUYER'
            -- Liên lạc được + còn sống (≤90d)
            WHEN source_contact_quality = 'real' AND recency_days <= 90 AND order_count > 1 THEN 'LIVE_CORE'
            WHEN source_contact_quality = 'real' AND recency_days <= 90 AND order_count = 1 THEN 'SECOND_ORDER'
            -- Mua lặp nhưng masked → Hug identity capture (683M CM treo sau định danh)
            WHEN source_contact_quality = 'masked' AND order_count > 1 THEN 'MASKED_REPEAT'
            -- Liên lạc được, nguội GẦN (91–365), giá trị → win-back ưu tiên
            WHEN source_contact_quality = 'real' AND recency_days BETWEEN 91 AND 365
                 AND (order_count > 1 OR value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER'))
                THEN 'DORMANT_VALUABLE'
            -- Liên lạc được, nguội XA (>365), từng mua lặp/giá trị → win-back ưu tiên thấp / test
            -- (tách khỏi GRAVEYARD: contactable + proven-repeat, đáng 1 shot rẻ rồi đo)
            WHEN source_contact_quality = 'real' AND recency_days > 365
                 AND (order_count > 1 OR value_group IN ('VALUE_VIP', 'VALUE_GOLD', 'VALUE_SILVER'))
                THEN 'LAPSED_VALUABLE'
            -- Nghĩa địa: masked one-time, bronze nguội, không liên lạc được
            ELSE 'GRAVEYARD'
        END AS strategic_tier
    FROM base
)

SELECT
    customer_key,
    customer_id,
    customer_code,
    full_name,
    customer_type,
    value_group,
    customer_status,
    order_count,
    recency_days,
    last_order_date,
    lifetime_value,
    lifetime_contribution_margin,
    channel_preference,
    is_contactable,
    source_contact_quality,
    contact_quality,
    strategic_tier,
    CASE strategic_tier
        WHEN 'LIVE_CORE'        THEN 'Liên lạc được · mua lặp · còn sống (≤90d) — NBA/CS giữ chân'
        WHEN 'SECOND_ORDER'     THEN 'Khách mới mua 1 lần (≤90d) — đẩy đơn 2'
        WHEN 'DORMANT_VALUABLE' THEN 'Liên lạc được · nguội gần ' || recency_days || 'd · có giá trị — win-back ưu tiên'
        WHEN 'LAPSED_VALUABLE'  THEN 'Liên lạc được · từng mua lặp/giá trị · nguội xa ' || recency_days || 'd — win-back thử'
        WHEN 'MASKED_REPEAT'    THEN 'Mua lặp (' || order_count || ' đơn) nhưng masked — Hug thu thập định danh'
        WHEN 'NONBUYER'         THEN 'Tạo nhưng chưa có đơn — nuôi lead sau'
        ELSE 'Nghĩa địa — suppress'
    END AS tier_reason,
    current_timestamp AS tier_generated_at
FROM tiered

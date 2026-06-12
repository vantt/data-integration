{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'dim'],
    post_hook=[
      "COPY (SELECT * FROM {{ this }}) TO '{{ get_rolling_location() }}' (FORMAT PARQUET)"
    ]
) }}

WITH customers AS (
    SELECT * FROM {{ ref('dim_customers_base') }}
),

metrics AS (
    SELECT * FROM {{ ref('int_customer_metrics') }}
),

economics AS (
    SELECT * FROM {{ ref('int_customer_economics') }}
),

joined_data AS (
    SELECT
        c.customer_key,
        c.customer_id,
        c.customer_code,
        c.full_name,
        c.email,
        c.phone,
        c.city,
        c.province,
        c.district,
        c.ward,
        c.address1,
        c.country,
        c.birth_date,
        c.gender,
        c.customer_group,
        c.loyalty_points,
        c.created_at,
        c.updated_at as source_updated_at,
        
        -- Metrics from intermediate model
        m.first_order_date,
        m.last_order_date,
        m.recency_days,
        m.frequency,
        m.monetary_value,
        m.lifespan_days,
        m.metric_calculated_at,

        -- P2 dimensions from intermediate model
        m.channel_preference,
        m.product_affinity,
        m.payment_behavior,

        -- P3 metrics from intermediate model
        m.avg_days_between_orders,
        m.avg_order_spend,
        m.discount_order_rate,
        m.cancel_rate,
        m.predicted_next_purchase_date,
        m.acquisition_source,

        -- [METRIC] Customer Status (RFM - Recency Component)
        -- Logic:
        -- - Active: Bought within the last 30 days.
        -- - At Risk: Bought between 31 and 90 days ago.
        -- - Churned: No purchase for over 90 days.
        CASE 
            WHEN m.recency_days <= 30 THEN 'Active'
            WHEN m.recency_days <= 90 THEN 'At Risk'
            WHEN m.recency_days > 90 THEN 'Churned'
            ELSE 'New/Unknown'
        END as customer_status,

        -- Economics from int_customer_economics (contribution margin; no overhead)
        e.lifetime_gross_profit,
        e.lifetime_contribution_margin,
        e.avg_order_contribution_margin_pct,
        e.margin_cogs_coverage_pct,
        e.is_margin_negative,

        -- Calculate a combined updated timestamp for incremental loading
        GREATEST(c.updated_at, COALESCE(m.metric_calculated_at, c.updated_at)) as last_modified_at

    FROM customers c
    LEFT JOIN metrics m ON c.customer_key = m.customer_key
    LEFT JOIN economics e ON c.customer_key = e.customer_key
)

SELECT
    customer_key,
    customer_id,
    customer_code,
    full_name,
    email,
    phone,
    city,
    province,
    district,
    ward,
    address1,
    country,
    
    -- customer_type: Commercial relationship type (Manual in Sapo)
    -- New scheme uses TYPE_* group codes (2026-04-19). Legacy groups whose code was
    -- not yet re-tagged still carry old codes/names — match those too so the migration
    -- backlog doesn't silently default to RETAIL. '%WHOLESALE%' catches both the new
    -- TYPE_WHOLESALE code and the legacy "WHOLESALE"/BANBUON group (name="WHOLESALE").
    -- See docs/context/customer-segmentation.md (§"Hướng dẫn triển khai trong Sapo").
    CASE
        WHEN customer_group LIKE '%WHOLESALE%' THEN 'WHOLESALE'                                    -- TYPE_WHOLESALE + legacy BANBUON
        WHEN customer_group LIKE '%TYPE_PARTNER%' OR customer_group LIKE '%KY_GUI%' THEN 'PARTNER'  -- + Ký Gửi (consignment/ký gửi)
        WHEN customer_group LIKE '%TYPE_STAFF%' THEN 'STAFF'
        WHEN customer_group LIKE '%TYPE_KOL%' THEN 'KOL'
        WHEN customer_group LIKE '%TYPE_CROSSBORDER%' OR customer_group LIKE '%CTN00014%' THEN 'CROSSBORDER'  -- US giao hàng hộ (người nhận VN)
        ELSE 'RETAIL'  -- Default: TYPE_RETAIL/BANLE, Selly (end-consumers), untagged
    END as customer_type,

    -- value_group: Customer value tier based on lifetime spend (Auto)
    CASE
        WHEN monetary_value >= 50000000 OR frequency >= 20 THEN 'VALUE_VIP'
        WHEN monetary_value >= 20000000 THEN 'VALUE_GOLD'
        WHEN monetary_value >= 5000000 THEN 'VALUE_SILVER'
        ELSE 'VALUE_BRONZE'
    END as value_group,

    -- lifecycle_stage: Customer lifecycle state (Auto)
    CASE
        WHEN lifespan_days <= 30 AND frequency <= 2 THEN 'LIFECYCLE_NEW'
        WHEN recency_days <= 90 THEN 'LIFECYCLE_ACTIVE'
        WHEN recency_days <= 180 THEN 'LIFECYCLE_AT_RISK'
        ELSE 'LIFECYCLE_CHURNED'
    END as lifecycle_stage,

    -- channel_preference: Preferred purchase channel (Auto from order history)
    channel_preference,

    -- product_affinity: Primary brand preference (Auto from sales history)
    product_affinity,

    -- payment_behavior: Payment pattern (Auto from payment history)
    payment_behavior,

    -- discount_sensitivity: How dependent on promotions to purchase (Auto from order history).
    -- NULL when customer has no qualifying (non-cancelled) orders to evaluate.
    CASE
        WHEN discount_order_rate IS NULL THEN NULL
        WHEN discount_order_rate > 0.7 THEN 'PROMO_DEPENDENT'
        WHEN discount_order_rate > 0.3 THEN 'PROMO_MIXED'
        ELSE 'FULL_PRICE'
    END AS discount_sensitivity,

    -- next_purchase_signal: Where customer is in their purchase cycle (Auto, NULL for 1-time buyers)
    CASE
        WHEN avg_days_between_orders IS NULL OR frequency <= 1 THEN NULL
        WHEN recency_days >= avg_days_between_orders * 1.5 THEN 'OVERDUE'
        WHEN recency_days >= avg_days_between_orders * 0.8 THEN 'DUE_SOON'
        ELSE 'ON_TRACK'
    END AS next_purchase_signal,

    -- geo_region: Geographic region (Auto from province)
    CASE
        WHEN province IN ('Hồ Chí Minh', 'TP Hồ Chí Minh', 'TP. Hồ Chí Minh', 'HCM', 'Ho Chi Minh') THEN 'GEO_HCMC'
        WHEN province IN ('Hà Nội', 'Ha Noi', 'Hanoi') THEN 'GEO_HANOI'
        WHEN province IN ('An Giang', 'Bạc Liêu', 'Bến Tre', 'Cà Mau', 'Cần Thơ', 'Đồng Tháp', 'Hậu Giang', 'Kiên Giang', 'Long An', 'Sóc Trăng', 'Tiền Giang', 'Trà Vinh', 'Vĩnh Long') THEN 'GEO_MEKONG'
        WHEN province IN ('Đà Nẵng', 'Thừa Thiên Huế', 'Quảng Nam', 'Quảng Ngãi', 'Bình Định', 'Phú Yên', 'Khánh Hòa', 'Ninh Thuận', 'Bình Thuận', 'Quảng Bình', 'Quảng Trị', 'Hà Tĩnh', 'Nghệ An', 'Thanh Hóa') THEN 'GEO_CENTRAL'
        WHEN province IS NULL OR province = '' THEN 'GEO_OTHER'
        ELSE 'GEO_OTHER'
    END as geo_region,

    -- acquisition_source: channel_name của ĐƠN ĐẦU TIÊN (từ int_customer_metrics).
    -- Kênh cụ thể (vd 'Zalo'), NULL nếu khách chưa có đơn. Test: relationships -> dim_channels.channel_name.
    acquisition_source,

    -- Demographics
    birth_date,
    gender,
    customer_group,  -- Keep raw Sapo value for reference
    loyalty_points,

    -- CLV & RFM
    COALESCE(monetary_value, 0) as lifetime_value,
    COALESCE(frequency, 0) as order_count,
    first_order_date,
    last_order_date,
    recency_days,
    lifespan_days,
    customer_status,

    -- Contribution margin economics (channel_net_profit basis; excludes overhead)
    COALESCE(lifetime_gross_profit, 0)              AS lifetime_gross_profit,
    COALESCE(lifetime_contribution_margin, 0)       AS lifetime_contribution_margin,
    avg_order_contribution_margin_pct,              -- NULL when no active orders
    margin_cogs_coverage_pct,                       -- NULL when no active orders
    COALESCE(is_margin_negative, FALSE)             AS is_margin_negative,

    -- P3 metrics
    avg_order_spend,
    avg_days_between_orders,
    discount_order_rate,
    cancel_rate,
    predicted_next_purchase_date,

    created_at,
    source_updated_at as updated_at,
    last_modified_at

FROM joined_data

{% if is_incremental() %}
-- Use source_updated_at (not last_modified_at) as watermark.
-- metric_calculated_at = current_timestamp on every run, which pushes the watermark
-- past new customers whose source updated_at predates the current run → they get silently skipped.
WHERE source_updated_at >= (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}

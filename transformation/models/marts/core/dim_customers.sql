{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
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

benchmarks AS (
    SELECT * FROM {{ ref('int_customer_benchmarks') }}
),

discount_metrics AS (
    SELECT * FROM {{ ref('int_customer_discount_metrics') }}
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
        c.address2,
        c.zip,
        c.company,
        c.address_phone,
        c.birth_date,
        c.gender,
        c.customer_group,
        c.customer_group_id,
        c.customer_group_code,
        c.customer_group_name,
        c.loyalty_points,
        c.status,
        c.assignee_id,
        c.tax_number,
        c.website,
        c.description,
        c.default_discount_rate,
        c.default_price_list_id,
        c.debt,
        c.loyalty_customer_json,
        c.social_customers_json,
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

        -- Discount metrics from int_customer_discount_metrics (4 buckets × 2 metrics)
        dm.last_line_discount_rate,
        dm.max_line_discount_rate,
        dm.last_voucher_discount_rate,
        dm.max_voucher_discount_rate,
        dm.last_campaign_discount_rate,
        dm.max_campaign_discount_rate,
        dm.last_negotiated_discount_rate,
        dm.max_negotiated_discount_rate,

        -- SKU-level product affinity (NULL = customer never purchased a paid line item)
        m.last_purchased_product,
        m.last_purchased_sku,
        m.top_affinity_product,
        m.top_affinity_sku,
        m.second_affinity_product,

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
        e.total_cogs,
        e.avg_gross_margin_pct,
        e.total_return_amount,
        e.return_count,
        e.cogs_order_count,

        -- Benchmark percentile columns (NULL for non-ranked customers; see benchmark_status)
        b.benchmark_status,
        b.lv_all_rankable_pct,
        b.lv_all_rankable_bucket,
        b.lv_all_rankable_phrase,
        b.lv_in_value_group_pct,
        b.lv_in_value_group_bucket,
        b.lv_in_value_group_phrase,
        b.lv_vg_frame_used,
        b.clv_all_rankable_pct,
        b.clv_all_rankable_bucket,
        b.clv_all_rankable_phrase,
        b.clv_in_value_group_pct,
        b.clv_in_value_group_bucket,
        b.clv_in_value_group_phrase,
        b.clv_vg_frame_used,
        b.clv_vs_rankable_median,

        -- Calculate a combined updated timestamp for incremental loading
        GREATEST(c.updated_at, COALESCE(m.metric_calculated_at, c.updated_at)) as last_modified_at

    FROM customers c
    LEFT JOIN metrics m ON c.customer_key = m.customer_key
    LEFT JOIN economics e ON c.customer_key = e.customer_key
    LEFT JOIN benchmarks b ON c.customer_key = b.customer_key
    LEFT JOIN discount_metrics dm ON c.customer_key = dm.customer_key
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
    address2,
    zip,
    company,
    address_phone,

    -- Sapo account-level attributes (raw from Sapo)
    status as sapo_status,
    assignee_id,
    tax_number,
    website,
    description as sapo_description,
    default_discount_rate,
    default_price_list_id,
    debt,

    -- JSON text columns (full objects; use json_extract in Metabase for specific fields)
    loyalty_customer_json,
    social_customers_json,

    -- customer_type: Commercial relationship type (Manual in Sapo)
    -- New scheme uses TYPE_* group codes (2026-04-19). Legacy groups whose code was
    -- not yet re-tagged still carry old codes/names — match those too so the migration
    -- backlog doesn't silently default to RETAIL. '%WHOLESALE%' catches both the new
    -- TYPE_WHOLESALE code and the legacy "WHOLESALE"/BANBUON group (name="WHOLESALE").
    -- See docs/context/customer-segmentation.md (§"Hướng dẫn triển khai trong Sapo").
    -- Refactored 2026-07-06 (plans/260619-0830-crm-tag-acl-sync/phase-00) to match against
    -- the parsed customer_group_code/customer_group_name columns instead of LIKE across the
    -- raw JSON blob (2nd undocumented parse point removed; group `id` is the stable ACL key,
    -- code/name can be renamed by Sapo — see dim_customers_base). Same substrings, same branches.
    CASE
        WHEN customer_group_code LIKE '%WHOLESALE%' OR customer_group_name LIKE '%WHOLESALE%'
            THEN 'WHOLESALE'                                    -- TYPE_WHOLESALE + legacy BANBUON
        WHEN customer_group_code LIKE '%TYPE_PARTNER%' OR customer_group_name LIKE '%TYPE_PARTNER%'
          OR customer_group_code LIKE '%KY_GUI%' OR customer_group_name LIKE '%KY_GUI%'
            THEN 'PARTNER'  -- + Ký Gửi (consignment/ký gửi)
        WHEN customer_group_code LIKE '%TYPE_STAFF%' OR customer_group_name LIKE '%TYPE_STAFF%'
            THEN 'STAFF'
        WHEN customer_group_code LIKE '%TYPE_KOL%' OR customer_group_name LIKE '%TYPE_KOL%'
            THEN 'KOL'
        WHEN customer_group_code LIKE '%TYPE_CROSSBORDER%' OR customer_group_name LIKE '%TYPE_CROSSBORDER%'
          OR customer_group_code LIKE '%CTN00014%' OR customer_group_name LIKE '%CTN00014%'
            THEN 'CROSSBORDER'  -- US giao hàng hộ (người nhận VN)
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

    -- SKU-level product affinity (NULL = customer never purchased a paid line item).
    -- last_purchased_*: SKU from most-recent active order (highest-quantity line wins multi-SKU tie).
    -- top/second_affinity_*: ranked by reorder frequency then quantity; second is NULL for 1-SKU customers.
    last_purchased_product,
    last_purchased_sku,
    top_affinity_product,
    top_affinity_sku,
    second_affinity_product,

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
    customer_group_id,    -- stable ACL key (Sapo group id; NULL for the legacy 'Unknown' literal)
    customer_group_code,  -- display/debug — NOT stable, Sapo has renamed group codes mid-flight
    customer_group_name,  -- display/debug — NOT stable, same caveat
    loyalty_points,

    -- CLV & RFM
    COALESCE(monetary_value, 0) as lifetime_value,
    COALESCE(frequency, 0) as order_count,
    first_order_date,
    last_order_date,
    recency_days,
    lifespan_days,
    customer_status,

    -- Contactable = has a usable phone number. No Zalo OA fallback; phone is the only
    -- reachable channel for CS/Sales outreach. Mirrors mart_customer_action_queue logic.
    (phone IS NOT NULL AND phone <> '') AS is_contactable,

    -- US gift-fulfilment recipients: CROSSBORDER customers are VN recipients whose packages
    -- are shipped from the US on behalf of overseas buyers. Group-code detection mirrors the
    -- customer_type CASE above (TYPE_CROSSBORDER or legacy CTN00014 group).
    -- Flag exposes the segment for filtering without requiring a self-join on customer_type.
    -- Refactored 2026-07-06 (phase-00) — matches parsed customer_group_code/name, not raw JSON.
    (customer_group_code LIKE '%TYPE_CROSSBORDER%' OR customer_group_name LIKE '%TYPE_CROSSBORDER%'
      OR customer_group_code LIKE '%CTN00014%' OR customer_group_name LIKE '%CTN00014%') AS is_us_gift_recipient,

    -- source_contact_quality: immutable — reflects whether the contact value is usable.
    -- '*' in phone = already obfuscated by source (relay/masked number from marketplace etc.).
    -- NULL or empty = no contact captured. Otherwise → real number.
    CASE
        WHEN phone IS NULL OR phone = '' OR phone LIKE '%*%' THEN 'masked'
        ELSE 'real'
    END AS source_contact_quality,

    -- contact_quality: mutable initial state; CRM staff upgrades to 'verified'
    -- via UpdateContactQuality. 'unverified' = real phone obtained, not yet confirmed reachable.
    CASE
        WHEN phone IS NULL OR phone = '' OR phone LIKE '%*%' THEN 'masked'
        ELSE 'unverified'
    END AS contact_quality,

    -- Contribution margin economics (channel_net_profit basis; excludes overhead)
    COALESCE(lifetime_gross_profit, 0)              AS lifetime_gross_profit,
    COALESCE(lifetime_contribution_margin, 0)       AS lifetime_contribution_margin,
    avg_order_contribution_margin_pct,              -- NULL when no active orders
    margin_cogs_coverage_pct,                       -- NULL when no active orders
    COALESCE(is_margin_negative, FALSE)             AS is_margin_negative,

    -- Pre-computed profitability/returns metrics (avoids live JOIN on C360 load)
    total_cogs,                                     -- NULL when no COGS-matched orders
    avg_gross_margin_pct,                           -- NULL when no COGS-matched orders
    total_return_amount,                            -- NULL when no return events
    return_count,                                   -- NULL when no return events
    cogs_order_count,                               -- NULL when no COGS-matched orders

    -- Cancel risk flag (threshold = 25%; derived from cancel_rate in joined_data)
    (cancel_rate > 0.25)                            AS is_high_cancel_risk,

    -- P3 metrics
    avg_order_spend,
    avg_days_between_orders,
    discount_order_rate,
    cancel_rate,
    predicted_next_purchase_date,

    -- Discount tracking: last + max rate per bucket (NULL = customer never had this type)
    -- Rates are 0.0–1.0 (not percentages). 4 buckets: line_discount / voucher / campaign / negotiated.
    -- See plans/260629-1215-customer-discount-tracking/ for taxonomy.
    last_line_discount_rate,
    max_line_discount_rate,
    last_voucher_discount_rate,
    max_voucher_discount_rate,
    last_campaign_discount_rate,
    max_campaign_discount_rate,
    last_negotiated_discount_rate,
    max_negotiated_discount_rate,

    -- Benchmark percentile rankings (populated for benchmark_status = 'ranked' only)
    -- benchmark_status: ranked | single_purchase | inactive_zero_value | non_retail
    -- *_pct: 0-100 percentile within the frame; *_bucket: bucket label; *_phrase: Vietnamese phrase for LLM
    benchmark_status,
    lv_all_rankable_pct,
    lv_all_rankable_bucket,
    lv_all_rankable_phrase,
    lv_in_value_group_pct,
    lv_in_value_group_bucket,
    lv_in_value_group_phrase,
    lv_vg_frame_used,
    clv_all_rankable_pct,
    clv_all_rankable_bucket,
    clv_all_rankable_phrase,
    clv_in_value_group_pct,
    clv_in_value_group_bucket,
    clv_in_value_group_phrase,
    clv_vg_frame_used,
    clv_vs_rankable_median,

    created_at,
    source_updated_at as updated_at,
    last_modified_at

FROM joined_data

{% if is_incremental() %}
-- Use source_updated_at (not last_modified_at) as watermark.
-- metric_calculated_at = current_timestamp on every run, which pushes the watermark
-- past new customers whose source updated_at predates the current run → they get silently skipped.
-- OR guard: catches new customers whose Sapo profile timestamp predates the watermark
-- (e.g. customer created long ago in Sapo, first order only now triggers int_customer_metrics).
WHERE source_updated_at >= (SELECT MAX(updated_at) FROM {{ this }})
   OR customer_key NOT IN (SELECT customer_key FROM {{ this }})
{% endif %}

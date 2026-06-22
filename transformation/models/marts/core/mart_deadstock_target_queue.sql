{{ config(
    tags=['mart', 'product', 'queue'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: DEADSTOCK TARGET QUEUE
-- =============================================================================
-- Dead-stock → customer targeting engine: cross-join own-brand FJV slow/dead SKUs
-- with customers who have previously purchased those exact SKUs and still belong
-- to an eligible strategic tier. One row per (product_key × customer_key).
--
-- PURPOSE: Drive two outreach legs —
--   HUG leg        : contactable customers (source_contact_quality='real')
--   SHOPEE_NATIVE  : masked-repeat buyers who cannot be directly messaged
--
-- SOURCES (all pre-computed — no raw re-joins, keeps model thin + deterministic):
--   mart_product_health  : slow/dead SKU universe with capital signals
--   fact_sales           : COMPLETED orders → past-buyer bridge (SKU × customer)
--   mart_customer_tier   : strategic tier assignment + contact quality
--   dim_customers        : replenishment signal + discount sensitivity enrich
--   dim_products         : brand_code filter (brand_code='FJV' is more complete
--                          than brand_name because some SKUs have brand_name=NULL)
--
-- GRAIN: (product_key, customer_key) — unique pair. Test enforced in schema.yml.
-- =============================================================================

WITH

-- ── 1. Own-brand FJV slow/dead SKU universe ──────────────────────────────────
-- Scope = dead OR underperforming (DOG/QUESTION) own-brand FJV with capital at risk.
-- Operational/unclassified categories excluded (not customer-clearable merchandise).
-- brand_code filter sourced from dim_products (more complete than mart_product_health.brand_name).
fjv_products AS (
    SELECT
        dp.product_key,
        dp.brand_code
    FROM {{ ref('dim_products') }} dp
    WHERE dp.brand_code = 'FJV'
    GROUP BY dp.product_key, dp.brand_code
),

slow_universe AS (
    SELECT
        ph.product_key,
        ph.sku,
        ph.product_name,
        ph.category,
        ph.health_class,
        ph.is_dead_stock,
        ph.dead_stock_value_at_risk,
        ph.stock_value_at_mac,
        ph.days_since_last_sale
    FROM {{ ref('mart_product_health') }} ph
    INNER JOIN fjv_products fp ON ph.product_key = fp.product_key
    WHERE
        -- SKU must be slow or dead (DOG/QUESTION by BCG class, or inventory dead-stock flag)
        (ph.is_dead_stock OR ph.health_class IN ('DOG', 'QUESTION'))
        -- Exclude operational supplies and uncategorized: not customer-clearable
        AND COALESCE(ph.category, 'Uncategorized') NOT IN ('Vận Hành', 'Uncategorized')
        -- Must have capital at risk (inventory cost) to be worth targeting
        AND (COALESCE(ph.dead_stock_value_at_risk, 0) + COALESCE(ph.stock_value_at_mac, 0)) > 0
),

-- ── 2. Past buyers: customers with COMPLETED orders for each target SKU ───────
-- INNER JOIN on product_key ensures only SKUs with ≥1 buyer enter the mart
-- (failed-launch SKUs with 0 buyers are naturally excluded).
-- status_key='8f7afecbc8fbc4cd0f50a57d1172482e' = COMPLETED (dim_order_status FK).
past_buyers AS (
    SELECT
        fs.product_key,
        fs.customer_key,
        SUM(fs.quantity)    AS buyer_sku_qty,
        MAX(fs.date_key)    AS buyer_sku_last_date
    FROM {{ ref('fact_sales') }} fs
    WHERE fs.status_key = '8f7afecbc8fbc4cd0f50a57d1172482e'
    GROUP BY fs.product_key, fs.customer_key
),

-- ── 3. Match: SKU universe × past buyers (INNER JOIN = 0-buyer SKUs excluded) ─
matched AS (
    SELECT
        su.product_key,
        su.sku,
        su.product_name,
        su.category,
        su.health_class,
        su.is_dead_stock,
        su.dead_stock_value_at_risk,
        su.stock_value_at_mac,
        su.days_since_last_sale,
        pb.customer_key,
        pb.buyer_sku_qty,
        pb.buyer_sku_last_date
    FROM slow_universe su
    INNER JOIN past_buyers pb ON su.product_key = pb.product_key
),

-- ── 4. Tier gate: only the 5 eligible strategic tiers ────────────────────────
-- GRAVEYARD (suppress, no data) and NONBUYER (never purchased) excluded.
tier_eligible AS (
    SELECT
        ct.customer_key,
        ct.full_name,
        ct.strategic_tier,
        ct.source_contact_quality,
        ct.value_group,
        ct.lifetime_value,
        ct.recency_days,
        ct.order_count,
        ct.is_contactable
    FROM {{ ref('mart_customer_tier') }} ct
    WHERE ct.strategic_tier IN (
        'LIVE_CORE',
        'SECOND_ORDER',
        'DORMANT_VALUABLE',
        'LAPSED_VALUABLE',
        'MASKED_REPEAT'
    )
),

-- ── 5. Enrich: replenishment signal + discount sensitivity from dim_customers ─
-- Also carries B2B markers (customer_type, acquisition_source) used to exclude
-- wholesale/dealer accounts downstream — they buy in bulk to resell, so a
-- consumer voucher + personal replenishment nudge is the wrong instrument.
customer_enrich AS (
    SELECT
        dc.customer_key,
        dc.next_purchase_signal,
        dc.predicted_next_purchase_date,
        dc.discount_sensitivity,
        dc.customer_type,
        dc.acquisition_source
    FROM {{ ref('dim_customers') }} dc
),

-- ── 6. Assemble full row ──────────────────────────────────────────────────────
assembled AS (
    SELECT
        -- Product spine
        m.product_key,
        m.sku,
        m.product_name,
        m.category,
        'FJV'                           AS brand_code,
        m.health_class,
        m.is_dead_stock,
        m.dead_stock_value_at_risk,
        m.stock_value_at_mac,
        m.days_since_last_sale,

        -- Customer identity
        m.customer_key,
        t.full_name,
        t.strategic_tier,
        t.source_contact_quality,

        -- Replenishment signals
        e.next_purchase_signal,
        e.predicted_next_purchase_date,
        e.discount_sensitivity,

        -- Value / RFM context (for rank priority and enrich)
        t.value_group,
        t.lifetime_value,
        t.recency_days,
        t.order_count,

        -- Buyer affinity for this specific SKU
        m.buyer_sku_qty,
        m.buyer_sku_last_date,

        -- ── Computed: routing channel ────────────────────────────────────────
        -- Contactable (real phone) → Hug touchpoint campaign
        -- Masked repeat → Shopee-native (Chat Broadcast / Repeat Buyer Voucher)
        CASE
            WHEN t.source_contact_quality = 'real' THEN 'HUG'
            ELSE 'SHOPEE_NATIVE'
        END                             AS route_channel,

        -- ── Computed: voucher eligibility ────────────────────────────────────
        -- FULL_PRICE buyers are price-insensitive; pushing a voucher cannibalises margin.
        -- NULL sensitivity (never discount-ordered) treated same as PROMO_DEPENDENT.
        CASE
            WHEN e.discount_sensitivity = 'FULL_PRICE' THEN FALSE
            ELSE TRUE
        END                             AS voucher_eligible,

        -- ── Computed: deterministic holdout (≈20%) ───────────────────────────
        -- Stable across runs: hash on (customer_key || sku) mod 10, keep 2 buckets.
        -- Used by P3 measurement to split treatment vs. control without randomising
        -- on re-run.
        (abs(hash(m.customer_key || m.sku)) % 10) < 2
                                        AS is_holdout

    FROM matched m
    INNER JOIN tier_eligible t  ON m.customer_key = t.customer_key
    LEFT  JOIN customer_enrich e ON m.customer_key = e.customer_key
    -- Keep B2C only. Wholesale/cross-border distributors and dealer-acquired
    -- accounts purchase in bulk to resell; excluding them keeps this a consumer
    -- clearance funnel and avoids burning vouchers on resale margin.
    WHERE COALESCE(e.customer_type, 'RETAIL') NOT IN ('WHOLESALE', 'CROSSBORDER')
      AND COALESCE(e.acquisition_source, '') <> 'Đại Lý'
)

-- ── 7. Final SELECT: rank + reason fragment ───────────────────────────────────
SELECT
    product_key,
    sku,
    product_name,
    category,
    brand_code,
    health_class,
    is_dead_stock,
    dead_stock_value_at_risk,
    stock_value_at_mac,
    days_since_last_sale,

    customer_key,
    full_name,
    strategic_tier,
    source_contact_quality,

    next_purchase_signal,
    predicted_next_purchase_date,
    discount_sensitivity,

    value_group,
    lifetime_value,
    recency_days,
    order_count,

    buyer_sku_qty,
    buyer_sku_last_date,

    route_channel,
    voucher_eligible,
    is_holdout,

    -- Rank within each SKU: replenishment-due buyers first, then value, then recency
    ROW_NUMBER() OVER (
        PARTITION BY product_key
        ORDER BY
            -- Replenishment-due customers surface first (overdue → best conversion signal)
            CASE next_purchase_signal
                WHEN 'OVERDUE'   THEN 1
                WHEN 'DUE_SOON'  THEN 2
                WHEN 'ON_TRACK'  THEN 3
                ELSE 4
            END ASC,
            -- Secondary: higher lifetime value = higher priority
            lifetime_value DESC NULLS LAST,
            -- Tertiary: more recent buyer = warmer lead
            recency_days ASC NULLS LAST
    )                                   AS target_rank,

    -- Human-readable reason fragment (Vietnamese, for CS context panel / Hug message)
    'Từng mua '
        || sku
        || ' ×' || buyer_sku_qty::VARCHAR
        || ', lần cuối ' || buyer_sku_last_date::VARCHAR
        || CASE next_purchase_signal
            WHEN 'OVERDUE'  THEN ' — đến nhịp tái mua (OVERDUE)'
            WHEN 'DUE_SOON' THEN ' — sắp đến nhịp tái mua'
            ELSE ''
           END
        || ' — đẩy thanh lý (vốn kẹt ~'
        || ROUND(
               (COALESCE(dead_stock_value_at_risk, 0) + COALESCE(stock_value_at_mac, 0))
               / 1000000.0, 1
           )::VARCHAR || 'M)'
                                        AS reason_fragment,

    current_timestamp                   AS queue_generated_at

FROM assembled
ORDER BY product_key, target_rank

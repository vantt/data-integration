{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Long-format cost ledger. Grain: 1 row per (order_id, cost_type).
-- Sources: COGS (Sapo-MAC primary / MISA TK632 fallback via int_order_cogs_reconciled),
--          Shopee revenue sheet (platform fees + taxes + shipping),
--          Sapo discount_items (seller vouchers, bundle deals, manual discounts).
-- Phase-05: COGS source changed from int_misa_sales_lines → int_order_cogs_reconciled.
-- Amounts are ALWAYS positive (ABS). Sign convention is derived from cost_category.
-- See docs/architecture/order-pl/order-pl-schema-design.md for taxonomy.

WITH order_meta AS (
    SELECT order_id, order_code, channel_key, date_key
    FROM {{ ref('fact_orders') }}
),

-- ============================================================
-- COGS — Phase-05: from int_order_cogs_reconciled (Sapo-MAC primary / MISA TK632 fallback)
-- ============================================================
cogs AS (
    SELECT
        om.order_id,
        r.order_code,
        'cogs'                              AS cost_type,
        'COGS'                              AS cost_category,
        ABS(SUM(COALESCE(r.cogs_goods_sapo, r.cogs_goods_misa, 0))) AS amount,
        -- Reflects actual data origin for traceability
        CASE
            WHEN BOOL_OR(r.cogs_goods_sapo IS NOT NULL) AND BOOL_OR(r.cogs_goods_misa IS NOT NULL) THEN 'sapo_v2_mac+misa'
            WHEN BOOL_OR(r.cogs_goods_sapo IS NOT NULL) THEN 'sapo_v2_mac'
            WHEN BOOL_OR(r.cogs_goods_misa IS NOT NULL) THEN 'misa'
            ELSE 'none'
        END                                 AS source_system,
        r.order_code                        AS source_record,
        'actual'                            AS fee_source,
        MIN(om.date_key)                    AS date_key,
        MIN(om.channel_key)                 AS channel_key
    FROM {{ ref('int_order_cogs_reconciled') }} r
    JOIN order_meta om ON r.order_code = om.order_code
    WHERE COALESCE(r.cogs_goods_sapo, r.cogs_goods_misa, 0) > 0
    GROUP BY om.order_id, r.order_code
),

-- ============================================================
-- Shopee platform fees, taxes, shipping — wide pivot → long
-- Source: stg_shopee_order_revenue (has all fee columns incl.
--   affiliate_commission_fee + piship_service_fee which are
--   NOT forwarded to int_shopee_order_fees)
-- ============================================================
shopee_wide AS (
    -- stg_shopee_order_revenue has core fees (service/payment/fixed/affiliate/piship)
    -- stg_shopee_order_service_fees holds the extra fees (infrastructure + voucher_xtra)
    -- int_shopee_order_fees merges them but drops individual columns for affiliate/piship,
    -- so we join both staging sources here directly.
    SELECT
        rev.order_code,
        om.order_id,
        om.date_key,
        om.channel_key,
        -- service_fee (D aggregate) removed: phase-07 drop — it == infra+voucher_xtra (F detail) → double-count
        rev.payment_fee,
        rev.fixed_fee,
        rev.affiliate_commission_fee,
        rev.piship_service_fee,
        COALESCE(svc.infrastructure_fee, 0) AS infrastructure_fee,
        COALESCE(svc.voucher_xtra_fee, 0)   AS voucher_xtra_fee,
        rev.vat_tax,
        rev.personal_income_tax,
        rev.total_shipping_net
    FROM {{ ref('stg_shopee_order_revenue') }} rev
    LEFT JOIN {{ ref('stg_shopee_order_service_fees') }} svc USING (order_code)
    JOIN order_meta om ON rev.order_code = om.order_code
),

shopee_fees AS (
    -- service_fee (D aggregate) dropped: == infra + voucher_xtra (F detail) → double-count. F detail is sole source.
    -- First arm carries the AS aliases that define the UNION column names (cost_type/cost_category/amount).
    SELECT order_id, order_code, 'platform_payment' AS cost_type, 'PLATFORM_FEE' AS cost_category, ABS(payment_fee) AS amount,             date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(payment_fee, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'platform_fixed',      'PLATFORM_FEE',              ABS(fixed_fee),                                            date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(fixed_fee, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'platform_affiliate',  'PLATFORM_FEE',              ABS(affiliate_commission_fee),                             date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(affiliate_commission_fee, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'platform_piship',     'PLATFORM_FEE',              ABS(piship_service_fee),                                   date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(piship_service_fee, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'platform_infra',      'PLATFORM_FEE',              ABS(infrastructure_fee),                                   date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(infrastructure_fee, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'platform_voucher_xtra','PLATFORM_FEE',             ABS(voucher_xtra_fee),                                     date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(voucher_xtra_fee, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'tax_vat',             'TAX',                       ABS(vat_tax),                                              date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(vat_tax, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'tax_pit',             'TAX',                       ABS(personal_income_tax),                                  date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(personal_income_tax, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'shipping_platform',   'SHIPPING',                  ABS(total_shipping_net),                                   date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(total_shipping_net, 0)) > 0
),

-- ============================================================
-- Sapo discounts — from std_order_discount_items (via stg_sapo_order_discount_items)
-- Classify by reason text pattern; aggregate same cost_type
-- per order (multiple same-type items can exist on one order)
-- ============================================================
sapo_discounts_classified AS (
    SELECT
        d.order_id,
        d.order_code,
        CASE
            WHEN d.reason ILIKE 'voucher seller:%' THEN 'discount_seller_voucher'
            WHEN d.reason = 'Bundle Deal'           THEN 'discount_bundle'
            WHEN d.reason = 'Seller Discount'       THEN 'discount_seller'
            ELSE                                         'discount_manual'
        END                          AS cost_type,
        'DISCOUNT'                   AS cost_category,
        ABS(d.amount)                AS amount,
        d.discount_rate              AS discount_rate,
        CASE
            WHEN d.reason ILIKE 'voucher seller:%'
                THEN 'voucher_promotional'
            WHEN d.reason = 'Bundle Deal'
                THEN 'bundle'
            WHEN d.reason ILIKE '%sampling%' OR d.reason ILIKE '%mẫu%' OR d.reason ILIKE '%tặng%'
                THEN 'sampling_gift'
            WHEN d.reason ILIKE '%đại lý%' OR d.reason ILIKE '%hợp đồng%' OR d.reason ILIKE '%nhà thuốc%'
                THEN 'wholesale_explicit'
            WHEN LOWER(d.reason) ILIKE '%mỹ%'
                OR TRIM(LOWER(d.reason)) = 'us'
                OR LOWER(d.reason) ILIKE '% us%'
                THEN 'overseas'
            WHEN d.reason ILIKE '%ctkm%' OR d.reason ILIKE '%father%' OR d.reason ILIKE '%mascot%'
                THEN 'campaign'
            WHEN d.reason ILIKE '%nhân viên%' OR d.reason ILIKE '%ctv%' OR d.reason ILIKE '%hoa hồng%'
                THEN 'employee_internal'
            WHEN d.discount_rate < 20
                THEN 'negotiated_micro'
            WHEN d.discount_rate < 40
                THEN 'negotiated_standard'
            ELSE
                'negotiated_deep'
        END AS discount_type,
        COALESCE(d.reason, '')       AS source_record,
        om.date_key,
        om.channel_key
    FROM {{ ref('std_order_discount_items') }} d
    JOIN order_meta om ON d.order_code = om.order_code
    WHERE d.amount > 0
),

sapo_discounts AS (
    SELECT
        order_id,
        order_code,
        cost_type,
        cost_category,
        SUM(amount)                        AS amount,
        MAX(discount_rate)                 AS discount_rate,
        MAX_BY(discount_type, amount)      AS discount_type,
        'sapo_v2'               AS source_system,
        MIN(source_record)   AS source_record,
        'actual'             AS fee_source,
        MIN(date_key)        AS date_key,
        MIN(channel_key)     AS channel_key
    FROM sapo_discounts_classified
    GROUP BY order_id, order_code, cost_type, cost_category
),

-- ============================================================
-- Promo goods cost — revenue=0 gift lines valued at Sapo-MAC
-- Marketing cost, NOT COGS (phase-03)
-- ============================================================
promo_goods AS (
    SELECT
        om.order_id,
        p.order_code,
        p.cost_type,
        p.cost_category,
        CAST(SUM(p.promo_goods_cost_amount) AS DECIMAL(18, 2)) AS amount,
        om.date_key,
        om.channel_key
    FROM {{ ref('int_order_promo_goods_cost') }} p
    JOIN order_meta om ON p.order_code = om.order_code
    GROUP BY om.order_id, p.order_code, p.cost_type, p.cost_category, om.date_key, om.channel_key
),

-- ============================================================
-- Overhead allocation — pro-rata pools spread to orders (phase-04)
-- One row per order × pool (e.g. overhead_admin, overhead_handling)
-- ============================================================
overhead AS (
    SELECT
        om.order_id,
        a.order_code,
        'overhead_' || a.pool_id                              AS cost_type,
        'OVERHEAD'                                            AS cost_category,
        CAST(ABS(a.allocated_amount) AS DECIMAL(18, 2))      AS amount,
        CASE WHEN a.is_overhead_estimated THEN 'estimated' ELSE 'actual' END AS fee_source,
        om.date_key, om.channel_key
    FROM {{ ref('int_order_overhead_allocation') }} a
    JOIN order_meta om ON a.order_code = om.order_code
)

-- ============================================================
-- Final union: all cost sources, uniform schema
-- ============================================================
SELECT
    order_id,
    order_code,
    cost_type,
    cost_category,
    CAST(amount AS DECIMAL(18, 2))  AS amount,
    NULL                            AS discount_rate,
    NULL                            AS discount_type,
    source_system,
    source_record,
    fee_source,
    date_key,
    channel_key
FROM cogs

UNION ALL

SELECT
    order_id,
    order_code,
    cost_type,
    cost_category,
    CAST(amount AS DECIMAL(18, 2))  AS amount,
    NULL                            AS discount_rate,
    NULL                            AS discount_type,
    'shopee'                        AS source_system,
    order_code                      AS source_record,
    'actual'                        AS fee_source,
    date_key,
    channel_key
FROM shopee_fees

UNION ALL

SELECT
    order_id,
    order_code,
    cost_type,
    cost_category,
    CAST(amount AS DECIMAL(18, 2))  AS amount,
    discount_rate,
    discount_type,
    source_system,
    source_record,
    fee_source,
    date_key,
    channel_key
FROM sapo_discounts

UNION ALL

SELECT
    order_id,
    order_code,
    cost_type,
    cost_category,
    amount,
    NULL                            AS discount_rate,
    NULL                            AS discount_type,
    'sapo_v2'                       AS source_system,
    order_code                      AS source_record,
    'actual'                        AS fee_source,
    date_key,
    channel_key
FROM promo_goods

UNION ALL

SELECT
    order_id,
    order_code,
    cost_type,
    cost_category,
    amount,
    NULL                            AS discount_rate,
    NULL                            AS discount_type,
    'derived'                       AS source_system,
    order_code                      AS source_record,
    fee_source,
    date_key,
    channel_key
FROM overhead

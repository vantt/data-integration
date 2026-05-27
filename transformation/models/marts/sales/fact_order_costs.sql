{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Long-format cost ledger. Grain: 1 row per (order_id, cost_type).
-- Sources: MISA (COGS), Shopee revenue sheet (platform fees + taxes + shipping),
--          Sapo discount_items (seller vouchers, bundle deals, manual discounts).
-- Amounts are ALWAYS positive (ABS). Sign convention is derived from cost_category.
-- See docs/architecture/order-pl-schema-design.md for taxonomy.

WITH order_meta AS (
    SELECT order_id, order_code, channel_key, date_key
    FROM {{ ref('fact_orders') }}
),

-- ============================================================
-- COGS — from MISA invoice lines (voucher_no = order_code)
-- ============================================================
cogs AS (
    SELECT
        om.order_id,
        m.voucher_no                        AS order_code,
        'cogs'                              AS cost_type,
        'COGS'                              AS cost_category,
        ABS(SUM(m.cogs_amount))             AS amount,
        'misa'                              AS source_system,
        m.voucher_no                        AS source_record,
        'actual'                            AS fee_source,
        MIN(om.date_key)                    AS date_key,
        MIN(om.channel_key)                 AS channel_key
    FROM {{ ref('int_misa_sales_lines') }} m
    JOIN order_meta om ON m.voucher_no = om.order_code
    WHERE m.cogs_amount IS NOT NULL
    GROUP BY om.order_id, m.voucher_no
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
        rev.service_fee,
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
    SELECT order_id, order_code, 'platform_service'     AS cost_type, 'PLATFORM_FEE' AS cost_category, ABS(service_fee)              AS amount, date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(service_fee, 0)) > 0
    UNION ALL
    SELECT order_id, order_code, 'platform_payment',    'PLATFORM_FEE',              ABS(payment_fee),                                          date_key, channel_key FROM shopee_wide WHERE ABS(COALESCE(payment_fee, 0)) > 0
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
-- Sapo discounts — from stg_sapo_order_discount_items
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
        COALESCE(d.reason, '')       AS source_record,
        om.date_key,
        om.channel_key
    FROM {{ ref('stg_sapo_order_discount_items') }} d
    JOIN order_meta om ON d.order_code = om.order_code
    WHERE d.amount > 0
),

sapo_discounts AS (
    SELECT
        order_id,
        order_code,
        cost_type,
        cost_category,
        SUM(amount)          AS amount,
        'sapo'               AS source_system,
        MIN(source_record)   AS source_record,
        'actual'             AS fee_source,
        MIN(date_key)        AS date_key,
        MIN(channel_key)     AS channel_key
    FROM sapo_discounts_classified
    GROUP BY order_id, order_code, cost_type, cost_category
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
    source_system,
    source_record,
    fee_source,
    date_key,
    channel_key
FROM sapo_discounts

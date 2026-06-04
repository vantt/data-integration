{{ config(
    tags=['int', 'cogs', 'promo'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INT: ORDER PROMO GOODS COST
-- =================================================================================================
-- Grain:   (order_code, sku) — one row per order × SKU with promo goods cost
-- Purpose: Identify giveaway/gift lines (revenue = 0) and value them at Sapo-MAC.
--          These are MARKETING COST, not COGS — excluded from TK632 COGS pool.
--
-- Gift-no-invoice case: cogs_source = 'sapo_mac' — Sapo carries the cost but no MISA
--   invoice exists (goods given away without revenue-recognition entry).
--
-- misa_642_amount: presence of TK642 sales-ledger entry on same (order_code, sku).
--   Carried for cross-tier reconciliation by phase-04 (overhead dedup).
--   NOTE: marketing cost, not COGS.
-- =================================================================================================

WITH line_rev AS (
    -- Bridge std_order_items (keyed by order_id) → order_code, aggregate revenue per (order_code, sku).
    -- INNER JOIN: restrict to orders present in fact_orders (rolling window).
    SELECT
        o.order_code,
        i.sku,
        SUM(i.line_amount) AS line_revenue
    FROM {{ ref('std_order_items') }} i
    JOIN {{ ref('fact_orders') }} o ON i.order_id = o.order_id
    GROUP BY o.order_code, i.sku
),

misa_642 AS (
    -- TK642 sales-ledger amount per (order_code, sku) for phase-04 reconciliation.
    SELECT
        voucher_no      AS order_code,
        product_code    AS sku,
        SUM(cogs_amount) AS misa_642_amount
    FROM {{ ref('std_misa_sales_lines') }}
    WHERE cost_account_group = '642'
    GROUP BY 1, 2
),

promo AS (
    -- STRICT promo filter: line_revenue = 0 (not COALESCE — avoids sweeping unmatched rows).
    -- Service SKUs excluded: same filter as int_order_cogs_reconciled.
    SELECT
        r.order_code,
        r.sku,
        r.variant_id,
        r.cogs_goods_primary AS promo_goods_cost_amount,
        lr.line_revenue,
        r.cogs_source
    FROM {{ ref('int_order_cogs_reconciled') }} r
    JOIN line_rev lr ON r.order_code = lr.order_code AND r.sku = lr.sku
    WHERE lr.line_revenue = 0                               -- STRICT: only true zero-revenue lines
      AND r.cogs_goods_primary IS NOT NULL                  -- must have a cost figure
      AND r.sku NOT LIKE 'DV%'
      AND r.sku NOT LIKE 'CPBH%'                           -- exclude service SKUs
)

SELECT
    p.order_code,
    p.sku,
    p.variant_id,
    p.promo_goods_cost_amount,
    p.line_revenue,
    p.cogs_source,

    -- Gift-no-invoice = Sapo has MAC but NO MISA entry at all (no 632 AND no 642).
    -- cogs_source='sapo_mac' only means "no 632 match" (recon model's MISA side is 632-only),
    -- so a 642-booked promo would also be 'sapo_mac' — exclude it via misa_642_amount IS NULL.
    (p.cogs_source = 'sapo_mac' AND m.misa_642_amount IS NULL) AS is_gift_no_invoice,
    (m.misa_642_amount IS NOT NULL) AS has_misa_642,
    m.misa_642_amount,

    'promo_goods_cost'              AS cost_type,
    'PROMO_GOODS'                   AS cost_category

FROM promo p
LEFT JOIN misa_642 m ON p.order_code = m.order_code AND p.sku = m.sku

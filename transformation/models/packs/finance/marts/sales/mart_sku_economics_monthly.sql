{{ config(
    tags=['mart', 'sales', 'sku', 'monthly'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: SKU Economics Monthly
-- =============================================================================
-- Single source of truth for SKU-level economics at monthly grain.
-- Replaces ad-hoc joins of int_misa_sales_lines + fact_sales + int_return_sku_lines
-- scattered across product_performance, product_profitability, and finance blueprints.
--
-- Grain: one row per (product_key, snapshot_month)
-- Window: rolling 24 months (sufficient for YoY analysis)
-- Status filter: excludes CANCELLED / Voided orders + Internal channels
--
-- CAVEATS (read before querying):
--
-- 1. COGS source priority: MISA invoice COGS is preferred (cogs_source='misa').
--    For SKUs without MISA coverage (bundles, untracked SKUs), Sapo MAC COGS from
--    fact_inventory_movements is used as fallback (cogs_source='sapo_mac').
--    Use the cogs_source column to distinguish which system supplied the COGS figure.
--    SKUs with no MISA match AND no inventory movements yield NULL (cogs_source=NULL).
--
-- 2. MISA join key: int_misa_sales_lines uses product_code (= SKU barcode / Sapo SKU).
--    Joined via dim_products.sku. Product_code mismatches between MISA and Sapo
--    (naming drift, bundles) will produce NULL MISA cogs; sapo_mac fallback applies.
--
-- 3. return_adjusted_margin_pct assumes WORST CASE: full refund_amount_allocated
--    is subtracted from gross_profit, implying no COGS recovery from returned goods.
--    This overstates the loss. True recovery requires return_status inspection per
--    line, which Sapo API does not expose at SKU level (Agent D caveat: order-level
--    only). Treat as a conservative lower bound.
--
-- 4. int_return_sku_lines approximation: return attribution is proportional by
--    line revenue within the originating order. When an order has multiple SKUs
--    and only one was returned, all SKUs in the order appear in int_return_sku_lines.
--    return_count / return_rate may overstate return exposure for minor SKUs.
--
-- 5. is_slow_mover proxy: computed from sales velocity alone (no fact_inventory).
--    days_since_last_sale measures days from snapshot_month_end to last observed
--    sale within the rolling window; actual on-hand stock is unknown.
--
-- 6. Channel concentration: only the single top channel by revenue is surfaced.
--    Full channel breakdown is JSON-heavy and deferred to blueprint-level queries.
--
-- 7. TWO margin metrics, DIFFERENT denominators — do not confuse:
--    - gross_margin_pct    = MISA-book margin (gross_profit / misa_revenue_net).
--    - realized_margin_pct = commercial margin (net_revenue - cogs_amount) / net_revenue,
--      on the ACTUAL Sapo selling price. Prefer realized_margin_pct for pricing/dashboards.
--    Pack-variant COGS depends on a correct misa_qty_multiplier (dim_sku_alias /
--    seed_sku_alias_manual): it must be 1 when MISA already records in the pack unit,
--    else COGS is overcounted x packsize (H010 SKUs fixed in seed, audited 2026-06-10).
--
-- Refresh: dbt build --select +mart_sku_economics_monthly
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Snapshot months: rolling 24 completed months (exclude current open month)
-- Same pattern as mart_customer_status_snapshot_monthly
-- ----------------------------------------------------------------------------
WITH snapshot_months AS (
    SELECT
        DATE_TRUNC('month', gs.month_start)::date AS snapshot_month
    FROM (
        SELECT unnest(generate_series(
            (DATE_TRUNC('month', current_date) - INTERVAL '24 months')::timestamp,
            (DATE_TRUNC('month', current_date) - INTERVAL '1 month')::timestamp,
            INTERVAL '1 month'
        )) AS month_start
    ) gs
),

-- ----------------------------------------------------------------------------
-- Product dimension: product_key + denormalized attributes + alias lookup for MISA
-- ----------------------------------------------------------------------------
-- product_code = Sapo SKU (preserved for output column compatibility).
-- misa_join_key  = effective key for MISA invoice lookup (= sku for base SKUs,
--                  = base/parent SKU for pack variants via dim_sku_alias).
-- misa_qty_multiplier = units per pack (1 for base, e.g. 30 for Metabo hộp).
-- ----------------------------------------------------------------------------
products AS (
    SELECT
        product_key,
        product_name,
        sku                                                AS product_code,
        misa_join_key,
        COALESCE(misa_qty_multiplier, 1)                   AS misa_qty_multiplier
    FROM {{ ref('dim_products') }}
    WHERE product_key != {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
),

-- ----------------------------------------------------------------------------
-- Sales lines from fact_sales (Sapo order items)
-- Excludes: cancelled/voided orders, internal channels, Unknown products
-- Joined to snapshot_months to assign each sale line to its snapshot month
-- ----------------------------------------------------------------------------
valid_channels AS (
    SELECT channel_key
    FROM {{ ref('dim_channels') }}
    WHERE is_sales_channel = true
),

sales_base AS (
    SELECT
        fs.product_key,
        fs.order_id,
        fs.channel_key,
        DATE_TRUNC('month', fs.ordered_at)::date AS snapshot_month,
        DATE(fs.ordered_at)                       AS sale_date,
        fs.quantity,
        fs.net_revenue                               AS line_revenue
    FROM {{ ref('fact_sales') }} fs
    -- Only sales channels (no internal / system)
    INNER JOIN valid_channels vc ON fs.channel_key = vc.channel_key
    -- Date range: 24 months back (match snapshot_months window)
    WHERE fs.ordered_at >= DATE_TRUNC('month', current_date) - INTERVAL '24 months'
      AND fs.ordered_at <  DATE_TRUNC('month', current_date)
      -- Exclude Unknown product
      AND fs.product_key != {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
      -- Revenue > 0 excludes gift/promo items at fact_sales level
      AND fs.net_revenue > 0
),

-- Order-level status filter: exclude cancelled orders
valid_orders AS (
    SELECT order_id
    FROM {{ ref('fact_orders') }}
    WHERE status != 'CANCELLED'
),

sales_filtered AS (
    SELECT sb.*
    FROM sales_base sb
    INNER JOIN valid_orders vo ON sb.order_id = vo.order_id
),

-- ----------------------------------------------------------------------------
-- CTE 1: Sales aggregates per (product_key, snapshot_month)
-- ----------------------------------------------------------------------------
sales_agg AS (
    SELECT
        product_key,
        snapshot_month,

        -- Volume
        SUM(quantity)                                           AS units_sold,
        SUM(line_revenue)                                       AS net_revenue,
        COUNT(DISTINCT order_id)                                AS order_count,

        -- Velocity inputs
        COUNT(DISTINCT sale_date)                               AS days_with_sales,
        MAX(sale_date)                                          AS last_sale_date
    FROM sales_filtered
    GROUP BY product_key, snapshot_month
),

-- ----------------------------------------------------------------------------
-- CTE 2: Total monthly revenue across all SKUs (for revenue_share_pct)
-- ----------------------------------------------------------------------------
monthly_totals AS (
    SELECT
        snapshot_month,
        SUM(net_revenue) AS total_month_revenue
    FROM sales_agg
    GROUP BY snapshot_month
),

-- ----------------------------------------------------------------------------
-- CTE 2b: Top-200 revenue threshold per month (for is_slow_mover)
-- Precomputed to avoid correlated subquery in final CTE
-- ----------------------------------------------------------------------------
top200_threshold AS (
    SELECT
        snapshot_month,
        MIN(net_revenue) AS threshold_revenue
    FROM (
        SELECT
            snapshot_month,
            net_revenue,
            ROW_NUMBER() OVER (
                PARTITION BY snapshot_month
                ORDER BY net_revenue DESC
            ) AS rn
        FROM sales_agg
    ) ranked
    WHERE rn <= 200
    GROUP BY snapshot_month
),

-- ----------------------------------------------------------------------------
-- CTE 3a: MISA per-unit costs aggregated at misa_join_key level
-- Computes cogs_per_misa_unit so we can apportion costs across Sapo pack variants
-- (e.g. base "chai" SKU and "hộp 10 chai" SKU both map to same MISA code).
-- Scope: NOT is_promo_line, NOT is_service_line, 24-month window
-- ----------------------------------------------------------------------------
misa_per_unit AS (
    SELECT
        product_code                                       AS misa_join_key,
        DATE_TRUNC('month', posting_date)::date            AS snapshot_month,
        SUM(quantity)                                      AS misa_total_qty,
        SUM(cogs_amount)                                   AS misa_total_cogs,
        SUM(revenue_net_of_discount)                       AS misa_total_revenue,
        CASE WHEN SUM(quantity) > 0
            THEN SUM(cogs_amount) / SUM(quantity)
        END                                                AS cogs_per_misa_unit,
        CASE WHEN SUM(quantity) > 0
            THEN SUM(revenue_net_of_discount) / SUM(quantity)
        END                                                AS revenue_per_misa_unit
    FROM {{ ref('int_misa_sales_lines') }}
    WHERE is_promo_line = false
      AND is_service_line = false
      AND posting_date >= DATE_TRUNC('month', current_date) - INTERVAL '24 months'
      AND posting_date <  DATE_TRUNC('month', current_date)
    GROUP BY product_code, DATE_TRUNC('month', posting_date)::date
),

-- CTE 3b: Apportion MISA cogs to each Sapo variant.
-- variant_cogs = variant_qty × misa_qty_multiplier × cogs_per_misa_unit.
-- This correctly handles pack variants (e.g. selling 2 "hộp 10" = 20 base units
-- against MISA's per-base-unit cost) and avoids double-counting when multiple
-- Sapo SKUs share one MISA code.
-- ----------------------------------------------------------------------------
misa_cogs AS (
    SELECT
        sa.product_key,
        sa.snapshot_month,
        sa.units_sold * p.misa_qty_multiplier                   AS misa_quantity,
        sa.units_sold * p.misa_qty_multiplier * mpu.cogs_per_misa_unit
                                                                AS cogs_amount,
        sa.units_sold * p.misa_qty_multiplier * mpu.revenue_per_misa_unit
                                                                AS misa_revenue_net,
        sa.units_sold * p.misa_qty_multiplier
            * (mpu.revenue_per_misa_unit - mpu.cogs_per_misa_unit)
                                                                AS gross_profit
    FROM sales_agg sa
    INNER JOIN products p     ON sa.product_key = p.product_key
    INNER JOIN misa_per_unit mpu
              ON p.misa_join_key = mpu.misa_join_key
             AND sa.snapshot_month = mpu.snapshot_month
    WHERE mpu.cogs_per_misa_unit IS NOT NULL
),

-- ----------------------------------------------------------------------------
-- CTE 3c: Sapo MAC COGS fallback — covers bundles + SKUs not tracked in MISA
-- Source: fact_inventory_movements, trans_type=301 (sale_order_fulfillment OUT legs only)
-- Joined to products CTE (already resolved dim_products) via sku → product_key.
-- Aggregated to (product_key, snapshot_month) to match misa_cogs grain.
-- Used only when mc.cogs_amount IS NULL in final CTE.
-- ----------------------------------------------------------------------------
sapo_mac_cogs AS (
    SELECT
        p.product_key,
        DATE_TRUNC('month', fim.issued_date_key)::date              AS snapshot_month,
        SUM(fim.cogs_amount)                                        AS sapo_mac_cogs_amount
    FROM {{ ref('fact_inventory_movements') }} fim
    INNER JOIN products p ON fim.sku = p.product_code
    WHERE fim.movement_direction = 'OUT'
      AND fim.trans_type = 301
      AND fim.issued_date_key >= DATE_TRUNC('month', current_date) - INTERVAL '24 months'
      AND fim.issued_date_key <  DATE_TRUNC('month', current_date)
    GROUP BY p.product_key, DATE_TRUNC('month', fim.issued_date_key)::date
),

-- ----------------------------------------------------------------------------
-- CTE 4: COGS per-unit trailing 3-month average (for variance metric)
-- Requires window over MISA data; computed from misa_cogs CTE
-- ----------------------------------------------------------------------------
cogs_trailing AS (
    SELECT
        product_key,
        snapshot_month,
        cogs_amount,
        misa_quantity,

        -- 3-month trailing average cogs_per_unit (inclusive of current month)
        -- Uses SUM over preceding 2 rows to get 3-month window
        SUM(cogs_amount) OVER (
            PARTITION BY product_key
            ORDER BY snapshot_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS cogs_3m_sum,
        SUM(misa_quantity) OVER (
            PARTITION BY product_key
            ORDER BY snapshot_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS qty_3m_sum
    FROM misa_cogs
),

-- ----------------------------------------------------------------------------
-- CTE 5: Returns from int_return_sku_lines, aggregated to (product_key, month)
-- ----------------------------------------------------------------------------
returns_agg AS (
    SELECT
        r.product_key,
        DATE_TRUNC('month', r.return_date)::date               AS snapshot_month,

        COUNT(DISTINCT r.return_id)                             AS return_count,
        SUM(r.sold_quantity)                                    AS return_quantity,
        SUM(r.refund_amount_allocated)                          AS refund_amount_allocated
    FROM {{ ref('int_return_sku_lines') }} r
    WHERE r.return_date >= DATE_TRUNC('month', current_date) - INTERVAL '24 months'
      AND r.return_date <  DATE_TRUNC('month', current_date)
    GROUP BY r.product_key, DATE_TRUNC('month', r.return_date)::date
),

-- ----------------------------------------------------------------------------
-- CTE 6: Top channel per (product_key, snapshot_month)
-- "Top" = channel with highest revenue within that SKU-month
-- ----------------------------------------------------------------------------
channel_revenue AS (
    SELECT
        sf.product_key,
        sf.snapshot_month,
        sf.channel_key,
        SUM(sf.line_revenue) AS channel_revenue
    FROM sales_filtered sf
    GROUP BY sf.product_key, sf.snapshot_month, sf.channel_key
),

channel_ranked AS (
    SELECT
        cr.product_key,
        cr.snapshot_month,
        cr.channel_key,
        cr.channel_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY cr.product_key, cr.snapshot_month
            ORDER BY cr.channel_revenue DESC
        ) AS rn,
        SUM(cr.channel_revenue) OVER (
            PARTITION BY cr.product_key, cr.snapshot_month
        ) AS total_sku_channel_revenue
    FROM channel_revenue cr
),

top_channel AS (
    SELECT
        cr.product_key,
        cr.snapshot_month,
        dc.channel_name                                         AS top_channel_name,
        ROUND(
            cr.channel_revenue * 100.0
            / NULLIF(cr.total_sku_channel_revenue, 0),
            2
        )                                                       AS top_channel_revenue_pct
    FROM channel_ranked cr
    LEFT JOIN {{ ref('dim_channels') }} dc ON cr.channel_key = dc.channel_key
    WHERE cr.rn = 1
),

-- ----------------------------------------------------------------------------
-- Final assembly: cross-join products × snapshot_months as spine,
-- then left-join each component CTE
-- Note: only snapshot_months where the SKU has at least one sale are included
-- (inner join on sales_agg, not cross-join, to keep table lean)
-- ----------------------------------------------------------------------------
final AS (
    SELECT
        -- ── Identity ─────────────────────────────────────────────────────────
        sa.product_key,
        p.product_code,
        p.product_name,
        sa.snapshot_month,

        -- ── Revenue & Volume ─────────────────────────────────────────────────
        sa.units_sold,
        sa.net_revenue,
        sa.order_count,
        ROUND(
            sa.units_sold::double / NULLIF(sa.days_with_sales, 0),
            4
        )                                                       AS daily_velocity,

        -- ── COGS & Margin (MISA preferred; sapo_mac fallback for bundles/untracked SKUs) ─
        COALESCE(mc.cogs_amount, smac.sapo_mac_cogs_amount)     AS cogs_amount,
        CASE
            WHEN mc.cogs_amount              IS NOT NULL THEN 'misa'
            WHEN smac.sapo_mac_cogs_amount   IS NOT NULL THEN 'sapo_mac'
            ELSE NULL
        END                                                     AS cogs_source,
        ROUND(
            COALESCE(mc.cogs_amount, smac.sapo_mac_cogs_amount)::double
            / NULLIF(sa.units_sold, 0),
            4
        )                                                       AS cogs_per_unit,
        COALESCE(mc.gross_profit, sa.net_revenue - smac.sapo_mac_cogs_amount)
                                                                AS gross_profit,
        -- DEPRECATED: column retained for schema compatibility; value intentionally NULL.
        -- Use realized_margin_pct instead (H010-corrected, Sapo net_revenue denominator).
        -- gross_margin_pct used MISA book revenue; H010 SKUs had uncorrected ~2× COGS error.
        -- Zero BI consumers confirmed (blueprints + rill + crm all use realized_margin_pct).
        CAST(NULL AS DOUBLE)                                    AS gross_margin_pct,

        -- ── Realized margin (Sapo net_revenue basis = true commercial margin) ─
        -- gross_margin_pct above is MISA-book (gross_profit / misa_revenue_net).
        -- realized_* uses ACTUAL Sapo net_revenue + COALESCE'd cogs_amount → the
        -- margin truly earned on the sale. Prefer for pricing/dashboards (CAVEAT #7).
        sa.net_revenue - COALESCE(mc.cogs_amount, smac.sapo_mac_cogs_amount)
                                                                AS realized_gross_profit,
        ROUND(
            (sa.net_revenue - COALESCE(mc.cogs_amount, smac.sapo_mac_cogs_amount)) * 100.0
            / NULLIF(sa.net_revenue, 0),
            4
        )                                                       AS realized_margin_pct,

        -- ── COGS Variance (vs 3-month trailing average) ──────────────────────
        ROUND(
            ct.cogs_3m_sum::double / NULLIF(ct.qty_3m_sum, 0),
            4
        )                                                       AS cogs_per_unit_3m_avg,
        CASE
            WHEN ct.qty_3m_sum > 0 AND ct.cogs_3m_sum > 0
                AND (ct.cogs_amount::double / NULLIF(mc.misa_quantity, 0)) IS NOT NULL
            THEN ROUND(
                (
                    (mc.cogs_amount::double / NULLIF(mc.misa_quantity, 0))
                    - (ct.cogs_3m_sum::double / NULLIF(ct.qty_3m_sum, 0))
                )
                * 100.0
                / NULLIF(ct.cogs_3m_sum::double / NULLIF(ct.qty_3m_sum, 0), 0),
                4
            )
            ELSE NULL
        END                                                     AS cogs_variance_pct,

        -- ── Returns ───────────────────────────────────────────────────────────
        COALESCE(ra.return_count, 0)                            AS return_count,
        COALESCE(ra.return_quantity, 0)                         AS return_quantity,
        COALESCE(ra.refund_amount_allocated, 0)                 AS refund_amount_allocated,
        ROUND(
            COALESCE(ra.return_count, 0)::double
            / NULLIF(sa.order_count, 0),
            4
        )                                                       AS return_rate,

        -- ── Return-Adjusted Margin (WORST CASE — see caveat #3) ──────────────
        -- Uses COALESCE gross_profit (misa preferred, sapo_mac fallback).
        -- Revenue base: misa_revenue_net for misa rows, sa.net_revenue for sapo_mac rows.
        CASE
            WHEN COALESCE(mc.gross_profit, sa.net_revenue - smac.sapo_mac_cogs_amount) IS NOT NULL
            THEN COALESCE(mc.gross_profit, sa.net_revenue - smac.sapo_mac_cogs_amount)
                 - COALESCE(ra.refund_amount_allocated, 0)
            ELSE NULL
        END                                                     AS return_adjusted_gross_profit,
        CASE
            WHEN mc.gross_profit IS NOT NULL AND mc.misa_revenue_net > 0
            THEN ROUND(
                (mc.gross_profit - COALESCE(ra.refund_amount_allocated, 0))
                * 100.0
                / NULLIF(mc.misa_revenue_net, 0),
                4
            )
            WHEN smac.sapo_mac_cogs_amount IS NOT NULL AND sa.net_revenue > 0
            THEN ROUND(
                (sa.net_revenue - smac.sapo_mac_cogs_amount - COALESCE(ra.refund_amount_allocated, 0))
                * 100.0
                / NULLIF(sa.net_revenue, 0),
                4
            )
            ELSE NULL
        END                                                     AS return_adjusted_margin_pct,

        -- ── Operational ───────────────────────────────────────────────────────
        -- days_since_last_sale: days from snapshot month-end to last observed sale
        DATE_DIFF(
            'day',
            sa.last_sale_date,
            (sa.snapshot_month + INTERVAL '1 month' - INTERVAL '1 day')::date
        )                                                       AS days_since_last_sale,
        -- is_slow_mover: no sale in final 14 days of month AND not a top-200 SKU
        -- Proxy without fact_inventory — see caveat #5
        (
            DATE_DIFF(
                'day',
                sa.last_sale_date,
                (sa.snapshot_month + INTERVAL '1 month' - INTERVAL '1 day')::date
            ) > 14
            AND sa.net_revenue < COALESCE(t200.threshold_revenue, 0)
        )                                                       AS is_slow_mover,
        ROUND(
            sa.net_revenue * 100.0
            / NULLIF(mt.total_month_revenue, 0),
            4
        )                                                       AS revenue_share_pct,
        CASE
            WHEN mc.cogs_amount IS NOT NULL
            THEN mc.gross_profit * 100.0 / NULLIF(mc.misa_revenue_net, 0) < 10
            WHEN smac.sapo_mac_cogs_amount IS NOT NULL
            THEN (sa.net_revenue - smac.sapo_mac_cogs_amount) * 100.0
                 / NULLIF(sa.net_revenue, 0) < 10
            ELSE FALSE
        END                                                     AS margin_outlier,

        -- ── Channel Concentration ─────────────────────────────────────────────
        tc.top_channel_name,
        tc.top_channel_revenue_pct

    FROM sales_agg sa
    INNER JOIN products p          ON sa.product_key = p.product_key
    LEFT  JOIN misa_cogs mc        ON sa.product_key = mc.product_key
                                  AND sa.snapshot_month = mc.snapshot_month
    LEFT  JOIN sapo_mac_cogs smac  ON sa.product_key = smac.product_key
                                  AND sa.snapshot_month = smac.snapshot_month
    LEFT  JOIN cogs_trailing ct    ON sa.product_key = ct.product_key
                                  AND sa.snapshot_month = ct.snapshot_month
    LEFT  JOIN returns_agg ra      ON sa.product_key = ra.product_key
                                  AND sa.snapshot_month = ra.snapshot_month
    LEFT  JOIN monthly_totals mt   ON sa.snapshot_month = mt.snapshot_month
    LEFT  JOIN top200_threshold t200 ON sa.snapshot_month = t200.snapshot_month
    LEFT  JOIN top_channel tc      ON sa.product_key = tc.product_key
                                  AND sa.snapshot_month = tc.snapshot_month
)

SELECT
    product_key,
    product_code,
    product_name,
    snapshot_month,

    -- Revenue & Volume
    units_sold,
    net_revenue,
    order_count,
    daily_velocity,

    -- COGS & Margin
    cogs_amount,
    cogs_source,
    cogs_per_unit,
    gross_profit,
    gross_margin_pct,
    realized_gross_profit,
    realized_margin_pct,

    -- COGS Variance
    cogs_per_unit_3m_avg,
    cogs_variance_pct,

    -- Returns
    return_count,
    return_quantity,
    refund_amount_allocated,
    return_rate,

    -- Return-Adjusted Margin
    return_adjusted_gross_profit,
    return_adjusted_margin_pct,

    -- Operational
    days_since_last_sale,
    is_slow_mover,
    revenue_share_pct,
    margin_outlier,

    -- Channel Concentration
    top_channel_name,
    top_channel_revenue_pct

FROM final
ORDER BY snapshot_month DESC, net_revenue DESC

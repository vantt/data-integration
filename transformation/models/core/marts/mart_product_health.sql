{{ config(
    tags=['mart', 'product', 'health'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: PRODUCT HEALTH
-- =============================================================================
-- Centerpiece product-health model. 1 row per product_key (current state).
-- Synthesis layer: velocity × margin × inventory × lifecycle.
-- Analog of dim_customers — replaces ad-hoc multi-join queries across
-- mart_sku_economics_monthly, mart_inventory_health, and int models.
--
-- SOURCES:
--   mart_sku_economics_monthly (latest month: economics primitives)
--   mart_inventory_health      (latest snapshot: inventory flags, aggregated across locations)
--   int_product_velocity_trend (velocity_90d, momentum, lifecycle dates)
--   int_product_discount_dependency (discount_dependency, discount_share)
--   dim_products               (category, brand_name)
--
-- CAVEATS:
--   1. health_class only populated for ~42 SKU with has_margin_data=true.
--      ~643 SKUs without MISA COGS get health_class=NULL; velocity/inventory
--      signals still populated.
--   2. Multi-location inventory aggregated: SUM on_hand/stock_value/dead_stock_value,
--      MIN days_of_supply (worst-case), MAX on boolean flags (any-location signal).
--   3. abc_class is overall-portfolio, not per-category.
--   4. velocity_90d sourced from int_product_velocity_trend (3-month rolling avg).
-- =============================================================================

WITH

-- ── Latest month economics ──────────────────────────────────────────────────
latest_econ AS (
    SELECT
        product_key,
        product_code                        AS sku,
        product_name,
        units_sold,
        net_revenue,
        daily_velocity,
        days_since_last_sale,
        revenue_share_pct,
        realized_margin_pct,
        cogs_variance_pct,
        margin_outlier,
        cogs_source,
        (realized_margin_pct IS NOT NULL)   AS has_margin_data
    FROM {{ ref('mart_sku_economics_monthly') }}
    WHERE snapshot_month = (
        SELECT MAX(snapshot_month) FROM {{ ref('mart_sku_economics_monthly') }}
    )
),

-- ── ABC class: cumulative net_revenue share across all-time history ─────────
abc_base AS (
    SELECT
        product_key,
        SUM(net_revenue)                                    AS total_revenue,
        SUM(SUM(net_revenue)) OVER ()                       AS grand_total
    FROM {{ ref('mart_sku_economics_monthly') }}
    GROUP BY product_key
),

abc_class AS (
    SELECT
        product_key,
        CASE
            WHEN SUM(total_revenue) OVER (
                ORDER BY total_revenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) / NULLIF(grand_total, 0) <= 0.80 THEN 'A'
            WHEN SUM(total_revenue) OVER (
                ORDER BY total_revenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) / NULLIF(grand_total, 0) <= 0.95 THEN 'B'
            ELSE 'C'
        END AS abc_class
    FROM abc_base
),

-- ── Latest inventory snapshot: aggregate across locations per product ────────
-- SUM   on_hand, stock_value, dead_stock_value (total exposure across warehouses)
-- MIN   days_of_supply (most constrained location drives restock urgency)
-- MAX   boolean flags  (any-location stockout/low-stock/dead-stock signals)
-- Per-product latest snapshot (NOT global max date): daily inventory snapshots are sparse
-- (each date covers only a few products), so global-max would miss most held stock.
-- Take each (product, location)'s most recent row, then aggregate to product.
latest_inv AS (
    SELECT
        product_key,
        SUM(on_hand)                            AS on_hand,
        SUM(stock_value_at_mac)                 AS stock_value_at_mac,
        SUM(dead_stock_value_at_risk)           AS dead_stock_value_at_risk,
        MIN(days_of_supply)                     AS days_of_supply,
        MAX(is_oos::INT)::BOOL                  AS is_oos,
        MAX(is_low_stock::INT)::BOOL            AS is_low_stock,
        MAX(is_dead_stock::INT)::BOOL           AS is_dead_stock
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY product_key, location_id
                ORDER BY snapshot_date DESC
            ) AS rn
        FROM {{ ref('mart_inventory_health') }}
    )
    WHERE rn = 1
    GROUP BY product_key
),

-- ── Velocity × margin NTILE scores (only over has_margin_data rows) ──────────
ntile_scores AS (
    SELECT
        e.product_key,
        NTILE(5) OVER (
            ORDER BY vt.velocity_90d NULLS LAST
        )                                       AS vel_score,
        NTILE(5) OVER (
            ORDER BY e.realized_margin_pct NULLS LAST
        )                                       AS margin_score
    FROM latest_econ e
    INNER JOIN {{ ref('int_product_velocity_trend') }} vt
        ON e.product_key = vt.product_key
    WHERE e.has_margin_data = TRUE
),

-- ── Product spine: things we SELL (recent sales) OR HOLD (inventory on hand) ──
-- Broaden beyond latest-month sellers so dormant/dead-stock products we still hold
-- appear (lifecycle DORMANT, health_class NULL) and become CLEAR_DEADSTOCK/DELIST targets.
product_spine AS (
    SELECT product_key FROM latest_econ
    UNION
    SELECT product_key FROM latest_inv WHERE on_hand > 0
),

-- ── Assemble all signals ─────────────────────────────────────────────────────
assembled AS (
    SELECT
        s.product_key,
        COALESCE(e.sku, dp.sku)                 AS sku,
        COALESCE(e.product_name, dp.product_name) AS product_name,
        dp.category,
        dp.brand_name,

        -- ABC
        ac.abc_class,

        -- Margin coverage flag (FALSE for inventory-only products with no economics)
        COALESCE(e.has_margin_data, FALSE)      AS has_margin_data,

        -- NTILE scores (NULL for no-margin rows)
        ns.vel_score,
        ns.margin_score,

        -- Health classification (NTILE-based, NULL when no margin data)
        CASE
            WHEN e.has_margin_data = FALSE THEN NULL
            WHEN ns.vel_score >= 4 AND ns.margin_score >= 4 THEN 'STAR'
            WHEN ns.vel_score >= 4 AND ns.margin_score <= 2 THEN 'WORKHORSE'
            WHEN ns.vel_score <= 2 AND ns.margin_score >= 4 THEN 'QUESTION'
            WHEN ns.vel_score <= 2 AND ns.margin_score <= 2 THEN 'DOG'
            ELSE 'BALANCED'
        END                                     AS health_class,

        -- Velocity momentum from int model
        vt.velocity_momentum,
        vt.velocity_90d,
        vt.first_sale_month,
        vt.months_active,

        -- Lifecycle stage: priority order matches business significance
        CASE
            WHEN (CURRENT_DATE - vt.first_sale_month::DATE) < 90 THEN 'NEW'
            WHEN COALESCE(e.days_since_last_sale, 999) > 90     THEN 'DORMANT'
            WHEN vt.velocity_momentum = 'DECELERATING'          THEN 'DECLINING'
            WHEN vt.velocity_momentum = 'ACCELERATING'          THEN 'GROWING'
            ELSE 'MATURE'
        END                                     AS lifecycle_stage,

        -- OOS risk: high-velocity or A-class SKU facing stockout
        (
            (
                COALESCE(inv.is_oos, FALSE)
                OR COALESCE(inv.is_low_stock, FALSE)
                OR COALESCE(inv.days_of_supply, 999) < 14
            )
            AND (COALESCE(ns.vel_score, 0) >= 3 OR ac.abc_class = 'A')
        )                                       AS oos_risk,

        -- Velocity / sales primitives
        e.daily_velocity,
        e.units_sold,
        e.revenue_share_pct,
        e.days_since_last_sale,

        -- Margin primitives (NULL when no COGS)
        e.realized_margin_pct,
        e.cogs_variance_pct,
        e.margin_outlier,

        -- Inventory primitives (NULL when product not in latest snapshot)
        inv.on_hand,
        inv.days_of_supply,
        inv.is_oos,
        inv.is_low_stock,
        inv.is_dead_stock,
        inv.stock_value_at_mac,
        inv.dead_stock_value_at_risk,

        -- Discount behaviour from int model
        dd.discount_dependency,
        dd.discount_share,

        current_timestamp                       AS calculated_at

    FROM product_spine s
    LEFT JOIN latest_econ e
        ON s.product_key = e.product_key
    LEFT JOIN (
        SELECT product_key,
               ANY_VALUE(sku)          AS sku,
               ANY_VALUE(product_name) AS product_name,
               ANY_VALUE(category)     AS category,
               ANY_VALUE(brand_name)   AS brand_name
        FROM {{ ref('dim_products') }}
        GROUP BY product_key
    ) dp
        ON s.product_key = dp.product_key
    LEFT JOIN abc_class ac
        ON s.product_key = ac.product_key
    LEFT JOIN latest_inv inv
        ON s.product_key = inv.product_key
    LEFT JOIN {{ ref('int_product_velocity_trend') }} vt
        ON s.product_key = vt.product_key
    LEFT JOIN {{ ref('int_product_discount_dependency') }} dd
        ON s.product_key = dd.product_key
    LEFT JOIN ntile_scores ns
        ON s.product_key = ns.product_key
)

SELECT
    product_key,
    sku,
    product_name,
    category,
    brand_name,

    -- Classification
    abc_class,
    has_margin_data,
    health_class,
    velocity_momentum,
    lifecycle_stage,
    oos_risk,

    -- Velocity & sales
    velocity_90d,
    daily_velocity,
    units_sold,
    revenue_share_pct,
    days_since_last_sale,

    -- Margin (null when cogs unavailable)
    realized_margin_pct,
    cogs_variance_pct,
    margin_outlier,

    -- Inventory (null when not in latest snapshot)
    on_hand,
    days_of_supply,
    is_oos,
    is_low_stock,
    is_dead_stock,
    stock_value_at_mac,
    dead_stock_value_at_risk,

    -- Discount behaviour
    discount_dependency,
    discount_share,

    calculated_at

FROM assembled
ORDER BY
    CASE abc_class WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,
    revenue_share_pct DESC NULLS LAST

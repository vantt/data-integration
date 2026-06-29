{{ config(
    materialized='table',
    tags=['mart', 'intermediate', 'customer']
) }}

-- =============================================================================
-- INTERMEDIATE: CUSTOMER × SKU SUPPLY TRACKING
-- =============================================================================
-- Grain: (customer_key, sku) — one row per customer per configured core SKU.
--
-- Computes estimated depletion date for each customer's most recent supply
-- of each of the 8 core Fine Japan SKUs, using recursive LAG stacking to
-- correctly handle early reorders (when customer buys before supply runs out).
--
-- Stacking logic (recursive CTE):
--   depletion(n) = GREATEST(purchase_date(n), depletion(n-1)) + effective_supply(n)
-- This ensures overlapping purchases accumulate correctly regardless of depth.
--
-- effective_supply = qty × supply_days_per_unit × dose_reduction_buffer
--   dose_reduction_buffer > 1 → customers use slower than standard (box lasts longer)
--   dose_reduction_buffer = 1 → customers use at standard dose
-- =============================================================================

WITH RECURSIVE config AS (
    SELECT * FROM {{ ref('seed_sku_regimen_config') }}
),

-- Active purchases of configured SKUs only, aggregated to day-grain.
-- Two branches UNIONed before GROUP BY:
--   Branch 1 — direct: fact_sales SKU matches config exactly.
--   Branch 2 — alias:  pack/combo SKU maps to a base config SKU via dim_sku_alias;
--              quantity multiplied by units_per_pack so supply accumulates correctly.
-- Branch 2 guards prevent double-counting:
--   • NOT IN config  — skip SKUs already handled by Branch 1
--   • pack ≠ base    — skip self-referential aliases (e.g. Metabo H030→H030 MISA entry)
raw_purchases AS (
    SELECT
        customer_key,
        sku, product_group, display_name,
        supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
        purchase_date,
        SUM(qty) AS total_qty
    FROM (
        -- Branch 1: individual SKU sold directly (pack_sku exactly in config)
        SELECT
            fs.customer_key,
            cfg.sku, cfg.product_group, cfg.display_name,
            cfg.supply_days_per_unit, cfg.dose_reduction_buffer,
            cfg.remind_lead_days, cfg.journey_enabled,
            CAST(fs.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS DATE) AS purchase_date,
            fs.quantity AS qty
        FROM {{ ref('fact_sales') }}   fs
        JOIN {{ ref('dim_products') }} dp  ON fs.product_key = dp.product_key
        JOIN config                   cfg ON dp.sku          = cfg.sku
        JOIN {{ ref('fact_orders') }}  fo  ON fs.order_id    = fo.order_id
        WHERE fo.is_active_order = TRUE

        UNION ALL

        -- Branch 2: pack/combo SKU → base config SKU via alias; qty × units_per_pack
        SELECT
            fs.customer_key,
            cfg.sku, cfg.product_group, cfg.display_name,
            cfg.supply_days_per_unit, cfg.dose_reduction_buffer,
            cfg.remind_lead_days, cfg.journey_enabled,
            CAST(fs.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS DATE) AS purchase_date,
            fs.quantity * da.units_per_pack AS qty
        FROM {{ ref('fact_sales') }}    fs
        JOIN {{ ref('dim_products') }}  dp  ON fs.product_key  = dp.product_key
        JOIN {{ ref('dim_sku_alias') }} da  ON dp.sku          = da.sapo_pack_sku
        JOIN config                    cfg ON da.sapo_base_sku = cfg.sku
        JOIN {{ ref('fact_orders') }}   fo  ON fs.order_id     = fo.order_id
        WHERE fo.is_active_order = TRUE
          AND dp.sku NOT IN (SELECT sku FROM config)
          AND da.sapo_pack_sku != da.sapo_base_sku
    )
    GROUP BY
        customer_key, sku, product_group, display_name,
        supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
        purchase_date
),

-- Assign row number per (customer, sku) for recursive traversal
purchases_numbered AS (
    SELECT
        *,
        ROUND(
            total_qty * supply_days_per_unit * dose_reduction_buffer
        )::INTEGER AS effective_supply_days,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key, sku
            ORDER BY purchase_date
        )::INTEGER  AS rn
    FROM raw_purchases
),

-- Recursive stacking: carry each purchase's actual stacked depletion forward
-- so the next purchase stacks on the accumulated window, not the raw window.
-- Column order matches the SELECT list in both anchor and recursive branches.
supply_stack (
    customer_key, sku, product_group, display_name,
    supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
    purchase_date, total_qty, effective_supply_days, depletion_date, rn
) AS (
    -- Anchor: first purchase per (customer, sku)
    SELECT
        customer_key, sku, product_group, display_name,
        supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
        purchase_date, total_qty, effective_supply_days,
        purchase_date + effective_supply_days,
        rn
    FROM purchases_numbered
    WHERE rn = 1

    UNION ALL

    -- Recursive: stack on previous stacked depletion date
    SELECT
        p.customer_key, p.sku, p.product_group, p.display_name,
        p.supply_days_per_unit, p.dose_reduction_buffer, p.remind_lead_days, p.journey_enabled,
        p.purchase_date, p.total_qty, p.effective_supply_days,
        GREATEST(p.purchase_date, s.depletion_date) + p.effective_supply_days,
        p.rn
    FROM purchases_numbered p
    JOIN supply_stack s
        ON  p.customer_key = s.customer_key
        AND p.sku          = s.sku
        AND p.rn           = s.rn + 1
),

-- Most recent order context per (customer, base_sku).
-- Computed here (not in mart) so last_order_code and last_purchase_date share the same
-- (customer, sku) grain — eliminates the dual-CTE desync that caused mismatched dates
-- and order codes in action card context chips.
-- Branch 2 divides by units_per_pack so last_net_unit_price is always per-base-unit.
last_order_ctx AS (
    SELECT
        customer_key,
        sku,
        last_order_code,
        last_sku_discount_rate,
        last_net_unit_price,
        ROW_NUMBER() OVER (PARTITION BY customer_key, sku ORDER BY ordered_at DESC) AS rn
    FROM (
        SELECT
            fs.customer_key,
            cfg.sku,
            fo.order_code                                               AS last_order_code,
            fs.discount_rate                                            AS last_sku_discount_rate,
            ROUND(fs.net_revenue / NULLIF(fs.quantity, 0))::BIGINT     AS last_net_unit_price,
            fs.ordered_at
        FROM {{ ref('fact_sales') }}   fs
        JOIN {{ ref('dim_products') }} dp  ON fs.product_key = dp.product_key
        JOIN config                   cfg ON dp.sku          = cfg.sku
        JOIN {{ ref('fact_orders') }}  fo  ON fs.order_id    = fo.order_id
        WHERE fo.is_active_order = TRUE

        UNION ALL

        SELECT
            fs.customer_key,
            cfg.sku,
            fo.order_code                                                                   AS last_order_code,
            fs.discount_rate                                                                AS last_sku_discount_rate,
            ROUND(fs.net_revenue / NULLIF(fs.quantity * da.units_per_pack, 0))::BIGINT     AS last_net_unit_price,
            fs.ordered_at
        FROM {{ ref('fact_sales') }}    fs
        JOIN {{ ref('dim_products') }}  dp  ON fs.product_key  = dp.product_key
        JOIN {{ ref('dim_sku_alias') }} da  ON dp.sku          = da.sapo_pack_sku
        JOIN config                    cfg ON da.sapo_base_sku = cfg.sku
        JOIN {{ ref('fact_orders') }}   fo  ON fs.order_id     = fo.order_id
        WHERE fo.is_active_order = TRUE
          AND dp.sku NOT IN (SELECT sku FROM config)
          AND da.sapo_pack_sku != da.sapo_base_sku
    )
)

-- Keep only the final (most recent) purchase row per (customer, sku)
SELECT
    s.customer_key,
    s.sku,
    s.product_group,
    s.display_name,
    s.supply_days_per_unit,
    s.dose_reduction_buffer,
    s.remind_lead_days,
    s.journey_enabled,
    s.purchase_date         AS last_purchase_date,
    s.total_qty             AS last_order_qty,
    s.effective_supply_days,
    s.depletion_date        AS estimated_depletion_date,
    loctx.last_order_code,
    loctx.last_sku_discount_rate,
    loctx.last_net_unit_price
FROM supply_stack s
LEFT JOIN last_order_ctx loctx
    ON  s.customer_key = loctx.customer_key
    AND s.sku          = loctx.sku
    AND loctx.rn = 1
QUALIFY s.rn = MAX(s.rn) OVER (PARTITION BY s.customer_key, s.sku)

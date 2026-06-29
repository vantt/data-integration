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

-- Active purchases of configured SKUs only, aggregated to day-grain
-- (handles multiple line items of same SKU in one order)
raw_purchases AS (
    SELECT
        fs.customer_key,
        cfg.sku,
        cfg.product_group,
        cfg.display_name,
        cfg.supply_days_per_unit,
        cfg.dose_reduction_buffer,
        cfg.remind_lead_days,
        cfg.journey_enabled,
        CAST(fs.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS DATE) AS purchase_date,
        SUM(fs.quantity)                                             AS total_qty
    FROM {{ ref('fact_sales') }}  fs
    JOIN {{ ref('dim_products') }} dp  ON fs.product_key  = dp.product_key
    JOIN config                   cfg ON dp.sku           = cfg.sku
    JOIN {{ ref('fact_orders') }}  fo  ON fs.order_id     = fo.order_id
    WHERE fo.is_active_order = TRUE
    GROUP BY
        fs.customer_key,
        cfg.sku, cfg.product_group, cfg.display_name,
        cfg.supply_days_per_unit, cfg.dose_reduction_buffer,
        cfg.remind_lead_days, cfg.journey_enabled,
        CAST(fs.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh' AS DATE)
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
)

-- Keep only the final (most recent) purchase row per (customer, sku)
SELECT
    customer_key,
    sku,
    product_group,
    display_name,
    supply_days_per_unit,
    dose_reduction_buffer,
    remind_lead_days,
    journey_enabled,
    purchase_date         AS last_purchase_date,
    total_qty             AS last_order_qty,
    effective_supply_days,
    depletion_date        AS estimated_depletion_date
FROM supply_stack
QUALIFY rn = MAX(rn) OVER (PARTITION BY customer_key, sku)

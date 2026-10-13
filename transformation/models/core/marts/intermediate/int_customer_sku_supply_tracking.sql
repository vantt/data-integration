{{ config(
    materialized='table',
    tags=['mart', 'intermediate', 'customer']
) }}

-- =============================================================================
-- INTERMEDIATE: CUSTOMER × SKU SUPPLY TRACKING
-- =============================================================================
-- Grain: (customer_key, sku, supply_stream) — one row per customer per configured
-- core SKU per supply stream.
--
-- supply_stream ∈ {'purchased', 'gift_only'}:
--   'purchased'  — customer has EVER bought this SKU non-gift (any order, not
--                  necessarily the same order as a gift line). ALL quantity for
--                  this stream (purchased + gift) accumulates into
--                  effective_supply_days exactly as before this dual-stream
--                  change — this is an intentional, unchanged behavior (a gift
--                  box on top of a real purchase habit still extends supply).
--   'gift_only'  — customer has NEVER bought this SKU non-gift; every line is a
--                  gift. Tracked independently so gift-only supply days don't
--                  bleed into (or get mistaken for) a real reorder cadence.
--                  Feeds the GIFT_TO_PURCHASE scenario (Phase 4).
-- ever_purchased is a STATIC per-(customer_key, sku) fact (not a chronological/
-- time-windowed check) — confirmed with user: no need to order gift vs.
-- purchase events by date; a single non-gift purchase, ever, is enough to
-- classify all of that customer×SKU's activity as 'purchased'.
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

-- Static per-(customer_key, sku) fact: has this customer EVER bought this SKU
-- with a real (non-gift) line? Two branches mirroring raw_purchases:
--   Direct branch — fact_sales SKU matches config exactly.
--   Pack/alias branch — pack/combo SKU maps to a base config SKU via
--     dim_sku_alias; a pack purchase still counts as a real purchase of the
--     base SKU (same guards as raw_purchases Branch 2 to avoid double-counting).
ever_purchased AS (
    SELECT DISTINCT fs.customer_key, cfg.sku
    FROM {{ ref('fact_sales') }}   fs
    JOIN {{ ref('dim_products') }} dp  ON fs.product_key = dp.product_key
    JOIN config                   cfg ON dp.sku          = cfg.sku
    JOIN {{ ref('fact_orders') }}  fo  ON fs.order_id    = fo.order_id
    WHERE fo.is_active_order = TRUE
      AND fs.is_gift_line = FALSE

    UNION

    SELECT DISTINCT fs.customer_key, cfg.sku
    FROM {{ ref('fact_sales') }}    fs
    JOIN {{ ref('dim_products') }}  dp  ON fs.product_key  = dp.product_key
    JOIN {{ ref('dim_sku_alias') }} da  ON dp.sku          = da.sapo_pack_sku
    JOIN config                    cfg ON da.sapo_base_sku = cfg.sku
    JOIN {{ ref('fact_orders') }}   fo  ON fs.order_id     = fo.order_id
    WHERE fo.is_active_order = TRUE
      AND fs.is_gift_line = FALSE
      AND dp.sku NOT IN (SELECT sku FROM config)
      AND da.sapo_pack_sku != da.sapo_base_sku
),

-- Active purchases of configured SKUs only, aggregated to day-grain.
-- Two branches UNIONed before GROUP BY:
--   Branch 1 — direct: fact_sales SKU matches config exactly.
--   Branch 2 — alias:  pack/combo SKU maps to a base config SKU via dim_sku_alias;
--              quantity multiplied by units_per_pack so supply accumulates correctly.
-- Branch 2 guards prevent double-counting:
--   • NOT IN config  — skip SKUs already handled by Branch 1
--   • pack ≠ base    — skip self-referential aliases (e.g. Metabo H030→H030 MISA entry)
--
-- supply_stream classification: LEFT JOIN ever_purchased (a static per-
-- customer-sku fact) makes supply_stream a per-(customer_key, sku) CONSTANT,
-- not a per-row value — so every raw line (gift or not) for a customer who
-- has ever purchased the SKU lands in 'purchased', and every line for a
-- customer who never has lands in 'gift_only' (which, by definition, can only
-- contain gift lines — there's nothing else to mix in).
raw_purchases AS (
    SELECT
        raw.customer_key,
        raw.sku, raw.product_group, raw.display_name,
        raw.supply_days_per_unit, raw.dose_reduction_buffer, raw.remind_lead_days, raw.journey_enabled,
        raw.purchase_date,
        CASE WHEN ep.customer_key IS NOT NULL THEN 'purchased' ELSE 'gift_only' END AS supply_stream,
        SUM(raw.qty) AS total_qty
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
    ) raw
    LEFT JOIN ever_purchased ep
        ON raw.customer_key = ep.customer_key AND raw.sku = ep.sku
    GROUP BY
        raw.customer_key, raw.sku, raw.product_group, raw.display_name,
        raw.supply_days_per_unit, raw.dose_reduction_buffer, raw.remind_lead_days, raw.journey_enabled,
        raw.purchase_date, supply_stream
),

-- Assign row number per (customer, sku, supply_stream) for recursive traversal
purchases_numbered AS (
    SELECT
        *,
        ROUND(
            total_qty * supply_days_per_unit * dose_reduction_buffer
        )::INTEGER AS effective_supply_days,
        ROW_NUMBER() OVER (
            PARTITION BY customer_key, sku, supply_stream
            ORDER BY purchase_date
        )::INTEGER  AS rn
    FROM raw_purchases
),

-- Recursive stacking: carry each purchase's actual stacked depletion forward
-- so the next purchase stacks on the accumulated window, not the raw window.
-- Column order matches the SELECT list in both anchor and recursive branches.
-- Partition/join keys now include supply_stream — the stacking FORMULA itself
-- (GREATEST(purchase_date, depletion_date) + effective_supply) is untouched.
supply_stack (
    customer_key, sku, supply_stream, product_group, display_name,
    supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
    purchase_date, total_qty, effective_supply_days, depletion_date, rn
) AS (
    -- Anchor: first purchase per (customer, sku, supply_stream)
    SELECT
        customer_key, sku, supply_stream, product_group, display_name,
        supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled,
        purchase_date, total_qty, effective_supply_days,
        purchase_date + effective_supply_days,
        rn
    FROM purchases_numbered
    WHERE rn = 1

    UNION ALL

    -- Recursive: stack on previous stacked depletion date
    SELECT
        p.customer_key, p.sku, p.supply_stream, p.product_group, p.display_name,
        p.supply_days_per_unit, p.dose_reduction_buffer, p.remind_lead_days, p.journey_enabled,
        p.purchase_date, p.total_qty, p.effective_supply_days,
        GREATEST(p.purchase_date, s.depletion_date) + p.effective_supply_days,
        p.rn
    FROM purchases_numbered p
    JOIN supply_stack s
        ON  p.customer_key   = s.customer_key
        AND p.sku            = s.sku
        AND p.supply_stream  = s.supply_stream
        AND p.rn             = s.rn + 1
),

-- Most recent order context per (customer, base_sku).
-- Computed here (not in mart) so last_order_code and last_purchase_date share the same
-- (customer, sku) grain — eliminates the dual-CTE desync that caused mismatched dates
-- and order codes in action card context chips.
-- Branch 2 divides by units_per_pack so last_net_unit_price is always per-base-unit.
--
-- last_sku_discount_rate: total effective discount = (line_discount + distributed_order_discount) / gross_price.
--   fact_sales.discount_rate is line-level only; distributed_discount_amount is the order-level
--   voucher/campaign discount pro-rated to this line. Both must be combined for the true rate.
--   Three cases:
--     1. No distributed discount → use line-level discount_rate as-is.
--     2. Both line + distributed → gross = discount_amount / discount_rate; total = (both) / gross.
--     3. No line discount but distributed exists → back-calculate gross via vat_ratio from fact_orders.
--
-- last_net_unit_price: actual price paid per unit (VAT-exclusive, after ALL discounts).
--   = (net_revenue − distributed_discount_vat_excl) / quantity
--   where distributed_discount_vat_excl = distributed_discount_amount × vat_ratio
--   vat_ratio = (total_collected − vat_amount) / total_collected  (from fact_orders)
-- SELF-CONTAINED CTE: has its own independent Branch1/Branch2 UNION (mirroring
-- raw_purchases, but computed separately since it selects last_order_code /
-- last_sku_discount_rate / last_net_unit_price, not qty aggregation) and its
-- own ROW_NUMBER() — it does NOT inherit raw_purchases' supply_stream. Each
-- branch below joins ever_purchased independently to classify supply_stream,
-- and ROW_NUMBER() now partitions by (customer_key, sku, supply_stream) so the
-- most-recent-order row is picked independently per stream.
last_order_ctx AS (
    SELECT
        customer_key,
        sku,
        supply_stream,
        last_order_code,
        last_sku_discount_rate,
        last_net_unit_price,
        ROW_NUMBER() OVER (PARTITION BY customer_key, sku, supply_stream ORDER BY ordered_at DESC) AS rn
    FROM (
        SELECT
            fs.customer_key,
            cfg.sku,
            CASE WHEN ep.customer_key IS NOT NULL THEN 'purchased' ELSE 'gift_only' END AS supply_stream,
            fo.order_code AS last_order_code,
            -- Effective total discount rate: line discount + pro-rated order discount
            CASE
                WHEN COALESCE(fs.distributed_discount_amount, 0) = 0
                    THEN fs.discount_rate
                WHEN fs.discount_rate > 0 AND fs.discount_amount > 0
                    THEN ROUND(
                        (fs.discount_amount + fs.distributed_discount_amount)
                        / NULLIF(fs.discount_amount / fs.discount_rate, 0),
                        4
                    )
                ELSE  -- no line discount; back-calculate VAT-incl gross from net_revenue and vat_ratio
                    ROUND(
                        fs.distributed_discount_amount
                        / NULLIF(
                            fs.net_revenue
                                * fo.total_collected
                                / NULLIF(fo.total_collected - COALESCE(fo.vat_amount, 0), 0)
                            + fs.distributed_discount_amount,
                            0
                        ),
                        4
                    )
            END AS last_sku_discount_rate,
            -- Actual price paid per unit: VAT-exclusive, after all discounts
            ROUND(
                (fs.net_revenue
                    - COALESCE(fs.distributed_discount_amount, 0)
                        * COALESCE(
                            (fo.total_collected - fo.vat_amount) / NULLIF(fo.total_collected, 0),
                            1
                        )
                ) / NULLIF(fs.quantity, 0)
            )::BIGINT AS last_net_unit_price,
            fs.ordered_at
        FROM {{ ref('fact_sales') }}   fs
        JOIN {{ ref('dim_products') }} dp  ON fs.product_key = dp.product_key
        JOIN config                   cfg ON dp.sku          = cfg.sku
        JOIN {{ ref('fact_orders') }}  fo  ON fs.order_id    = fo.order_id
        LEFT JOIN ever_purchased ep ON fs.customer_key = ep.customer_key AND cfg.sku = ep.sku
        WHERE fo.is_active_order = TRUE

        UNION ALL

        SELECT
            fs.customer_key,
            cfg.sku,
            CASE WHEN ep.customer_key IS NOT NULL THEN 'purchased' ELSE 'gift_only' END AS supply_stream,
            fo.order_code AS last_order_code,
            CASE
                WHEN COALESCE(fs.distributed_discount_amount, 0) = 0
                    THEN fs.discount_rate
                WHEN fs.discount_rate > 0 AND fs.discount_amount > 0
                    THEN ROUND(
                        (fs.discount_amount + fs.distributed_discount_amount)
                        / NULLIF(fs.discount_amount / fs.discount_rate, 0),
                        4
                    )
                ELSE
                    ROUND(
                        fs.distributed_discount_amount
                        / NULLIF(
                            fs.net_revenue
                                * fo.total_collected
                                / NULLIF(fo.total_collected - COALESCE(fo.vat_amount, 0), 0)
                            + fs.distributed_discount_amount,
                            0
                        ),
                        4
                    )
            END AS last_sku_discount_rate,
            ROUND(
                (fs.net_revenue
                    - COALESCE(fs.distributed_discount_amount, 0)
                        * COALESCE(
                            (fo.total_collected - fo.vat_amount) / NULLIF(fo.total_collected, 0),
                            1
                        )
                ) / NULLIF(fs.quantity * da.units_per_pack, 0)
            )::BIGINT AS last_net_unit_price,
            fs.ordered_at
        FROM {{ ref('fact_sales') }}    fs
        JOIN {{ ref('dim_products') }}  dp  ON fs.product_key  = dp.product_key
        JOIN {{ ref('dim_sku_alias') }} da  ON dp.sku          = da.sapo_pack_sku
        JOIN config                    cfg ON da.sapo_base_sku = cfg.sku
        JOIN {{ ref('fact_orders') }}   fo  ON fs.order_id     = fo.order_id
        LEFT JOIN ever_purchased ep ON fs.customer_key = ep.customer_key AND cfg.sku = ep.sku
        WHERE fo.is_active_order = TRUE
          AND dp.sku NOT IN (SELECT sku FROM config)
          AND da.sapo_pack_sku != da.sapo_base_sku
    )
)

-- Keep only the final (most recent) purchase row per (customer, sku, supply_stream)
SELECT
    s.customer_key,
    s.sku,
    s.supply_stream,
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
    ON  s.customer_key    = loctx.customer_key
    AND s.sku             = loctx.sku
    AND s.supply_stream   = loctx.supply_stream
    AND loctx.rn = 1
QUALIFY s.rn = MAX(s.rn) OVER (PARTITION BY s.customer_key, s.sku, s.supply_stream)

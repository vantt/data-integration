{{ config(
    tags=['mart', 'sales', 'inventory', 'health'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: INVENTORY HEALTH
-- =============================================================================
-- Grain: 1 row per (variant_id, location_id, snapshot_date)
-- Materialization: external parquet (full rebuild — small table, fast)
--
-- Health signals derived from fact_inventory_snapshot + mart_sku_economics_monthly:
--   is_oos             — on_hand <= 0 (out of stock)
--   is_low_stock       — 0 < on_hand <= min_value (reorder threshold breached)
--   is_overstock       — on_hand > max_value (when max threshold set)
--   days_of_supply     — on_hand / daily_velocity from last completed month
--   is_slow_mover      — days_of_supply > 90 OR no sales in 30 days
--   is_dead_stock      — no sales in 90 days (proxy via mart_sku_economics_monthly)
--   stock_value_at_mac — on_hand × mac (capital tied up)
--   committed_value_at_mac — committed × mac (already sold, pending fulfillment)
--
-- CAVEATS:
--   1. daily_velocity sourced from last completed month in mart_sku_economics_monthly.
--      SKUs with no sales history get NULL daily_velocity → days_of_supply = NULL.
--   2. is_slow_mover and is_dead_stock are proxies based on sales recency in
--      mart_sku_economics_monthly (rolling 24 months). SKUs outside that window
--      appear as dead stock regardless of actual inventory movement.
--   3. Location-level velocity is not available — daily_velocity is SKU-level
--      aggregate across all channels. Per-location sell-through rates require
--      order location attribution (future work).
--   4. mac (Moving Average Cost) from Sapo may lag true cost for recent receipts.
--      stock_value_at_mac is an estimate, not accounting-grade.
-- =============================================================================

WITH snapshot AS (
    SELECT
        inventory_snapshot_key,
        variant_id,
        location_id,
        snapshot_date,
        product_key,
        sku,
        product_id,
        product_name,
        category,
        category_code,
        brand_name,
        brand_code,
        location_name,
        location_code,
        on_hand,
        available,
        committed,
        incoming,
        onway,
        min_value,
        max_value,
        mac,
        stock_value_at_mac,
        committed_value_at_mac,
        bin_location,
        wait_to_pack,
        source_timestamp
    FROM {{ ref('fact_inventory_snapshot') }}
),

-- Latest completed month velocity from mart_sku_economics_monthly
-- Use the most recent snapshot_month available per SKU for days_of_supply calc
velocity AS (
    SELECT
        product_key,
        snapshot_month,
        daily_velocity,
        days_since_last_sale,
        is_slow_mover     AS sku_is_slow_mover_sales,
        ROW_NUMBER() OVER (
            PARTITION BY product_key
            ORDER BY snapshot_month DESC
        ) AS rn
    FROM {{ ref('mart_sku_economics_monthly') }}
    WHERE daily_velocity IS NOT NULL
),

latest_velocity AS (
    SELECT
        product_key,
        snapshot_month       AS velocity_month,
        daily_velocity,
        days_since_last_sale,
        sku_is_slow_mover_sales
    FROM velocity
    WHERE rn = 1
)

SELECT
    -- ── Identity ─────────────────────────────────────────────────────────────
    s.inventory_snapshot_key,
    s.variant_id,
    s.location_id,
    s.snapshot_date,
    s.product_key,
    s.sku,
    s.product_id,
    s.product_name,
    s.category,
    s.category_code,
    s.brand_name,
    s.brand_code,
    s.location_name,
    s.location_code,

    -- ── Stock levels ─────────────────────────────────────────────────────────
    s.on_hand,
    s.available,
    s.committed,
    s.incoming,
    s.onway,
    s.min_value,
    s.max_value,
    s.mac,
    s.stock_value_at_mac,
    s.committed_value_at_mac,
    s.bin_location,
    s.wait_to_pack,

    -- ── Health flags ─────────────────────────────────────────────────────────

    -- OOS: no units on hand (includes negative consignment stock)
    (s.on_hand <= 0)                                                        AS is_oos,

    -- Low stock: above zero but at or below the Sapo min threshold
    -- Only meaningful when min_value is configured (non-null, non-zero)
    (
        s.on_hand > 0
        AND s.min_value IS NOT NULL
        AND s.min_value > 0
        AND s.on_hand <= s.min_value
    )                                                                       AS is_low_stock,

    -- Overstock: above Sapo max threshold
    (
        s.max_value IS NOT NULL
        AND s.max_value > 0
        AND s.on_hand > s.max_value
    )                                                                       AS is_overstock,

    -- ── Velocity-derived metrics ─────────────────────────────────────────────

    -- Source month used for velocity (for audit)
    lv.velocity_month,
    lv.daily_velocity,

    -- Days of supply: how many days current stock will last at recent sales rate
    -- NULL when no sales history or daily_velocity = 0
    CASE
        WHEN s.on_hand > 0
             AND lv.daily_velocity IS NOT NULL
             AND lv.daily_velocity > 0
        THEN ROUND(s.on_hand / lv.daily_velocity, 1)
        WHEN s.on_hand <= 0
        THEN 0.0
        ELSE NULL
    END                                                                     AS days_of_supply,

    -- Slow mover: days_of_supply > 90 OR no sale in last 30 days
    (
        -- No velocity data at all (never sold in 24-month window)
        lv.product_key IS NULL
        -- OR last sale was more than 30 days ago
        OR COALESCE(lv.days_since_last_sale, 9999) > 30
        -- OR supply will last more than 90 days at current pace
        OR (
            s.on_hand > 0
            AND lv.daily_velocity > 0
            AND (s.on_hand / lv.daily_velocity) > 90
        )
    )                                                                       AS is_slow_mover,

    -- Dead stock: no sale in last 90 days (stricter threshold)
    (
        lv.product_key IS NULL
        OR COALESCE(lv.days_since_last_sale, 9999) > 90
    )                                                                       AS is_dead_stock,

    -- Dollar exposure of slow/dead stock (capital at risk)
    CASE
        WHEN (
            lv.product_key IS NULL
            OR COALESCE(lv.days_since_last_sale, 9999) > 30
        )
        THEN s.stock_value_at_mac
        ELSE 0
    END                                                                     AS slow_mover_value_at_risk,

    CASE
        WHEN (
            lv.product_key IS NULL
            OR COALESCE(lv.days_since_last_sale, 9999) > 90
        )
        THEN s.stock_value_at_mac
        ELSE 0
    END                                                                     AS dead_stock_value_at_risk,

    -- ── Metadata ─────────────────────────────────────────────────────────────
    s.source_timestamp

FROM snapshot s
LEFT JOIN latest_velocity lv
    ON s.product_key = lv.product_key

ORDER BY s.snapshot_date DESC, s.location_id, s.stock_value_at_mac DESC NULLS LAST

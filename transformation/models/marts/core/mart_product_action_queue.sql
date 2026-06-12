{{ config(
    tags=['mart', 'product', 'queue'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: PRODUCT ACTION QUEUE
-- =============================================================================
-- Operational action queue: one row per product requiring merchandising action.
-- Grain: product_key (only where action_type IS NOT NULL).
-- Analog of mart_customer_action_queue — drives detailView Actions tab and
-- daily Merchandising / Inventory / Marketing workflow.
--
-- ACTION TYPES (priority order):
--   RESTOCK_NOW      — OOS-risk STAR/A-class facing imminent stockout
--   CLEAR_DEADSTOCK  — dead stock with capital at risk
--   REVIEW_MARGIN    — margin outlier / COGS drift / WORKHORSE declining
--   PROMOTE          — QUESTION (high margin, low velocity) — expose to demand
--   DELIST           — DOG + dead stock (no velocity, no margin, capital stuck)
--
-- SOURCE: mart_product_health (reads already-computed health signals; no
-- re-joining raw marts to keep this model thin and deterministic)
-- =============================================================================

WITH

-- Average unit price from latest month (used in value_at_stake estimates).
-- Pre-computed as CTE to avoid correlated subqueries which break on parquet sources.
avg_unit_price AS (
    SELECT
        product_key,
        net_revenue / NULLIF(units_sold, 0) AS avg_unit_price
    FROM {{ ref('mart_sku_economics_monthly') }}
    WHERE snapshot_month = (
        SELECT MAX(snapshot_month) FROM {{ ref('mart_sku_economics_monthly') }}
    )
),

products AS (
    SELECT
        ph.product_key,
        ph.sku,
        ph.product_name,
        ph.category,
        ph.brand_name,

        -- Classification signals
        ph.abc_class,
        ph.health_class,
        ph.velocity_momentum,
        ph.lifecycle_stage,
        ph.oos_risk,
        ph.has_margin_data,

        -- Velocity / revenue context for rationale strings
        ph.velocity_90d,
        ph.daily_velocity,
        ph.units_sold,
        ph.revenue_share_pct,
        ph.days_since_last_sale,

        -- Margin signals
        ph.realized_margin_pct,
        ph.cogs_variance_pct,
        ph.margin_outlier,

        -- Inventory signals
        ph.on_hand,
        ph.days_of_supply,
        ph.is_oos,
        ph.is_low_stock,
        ph.is_dead_stock,
        ph.stock_value_at_mac,
        ph.dead_stock_value_at_risk,

        -- Discount context
        ph.discount_dependency,

        -- Unit price for value_at_stake calculations
        aup.avg_unit_price

    FROM {{ ref('mart_product_health') }} ph
    LEFT JOIN avg_unit_price aup ON ph.product_key = aup.product_key
),

classified AS (
    SELECT
        *,
        -- Priority cascade — first matching branch wins.
        -- Restock urgency is highest: losing STAR/A-class sales to OOS costs revenue now.
        CASE
            WHEN oos_risk
                THEN 'RESTOCK_NOW'
            WHEN COALESCE(is_dead_stock, FALSE)
                 AND COALESCE(dead_stock_value_at_risk, 0) > 0
                THEN 'CLEAR_DEADSTOCK'
            WHEN COALESCE(margin_outlier, FALSE)
                 OR COALESCE(cogs_variance_pct, 0) > 0.20
                 OR (health_class = 'WORKHORSE' AND velocity_momentum = 'DECELERATING')
                THEN 'REVIEW_MARGIN'
            WHEN health_class = 'QUESTION'
                THEN 'PROMOTE'
            WHEN health_class = 'DOG'
                 AND COALESCE(is_dead_stock, FALSE)
                THEN 'DELIST'
            ELSE NULL
        END AS action_type
    FROM products
)

SELECT
    product_key,
    sku,
    product_name,
    category,
    brand_name,

    -- Health context
    abc_class,
    health_class,
    velocity_momentum,
    lifecycle_stage,
    has_margin_data,

    -- Action assignment
    action_type,

    -- Priority rank (lower = more urgent)
    CASE action_type
        WHEN 'RESTOCK_NOW'     THEN 1
        WHEN 'CLEAR_DEADSTOCK' THEN 2
        WHEN 'REVIEW_MARGIN'   THEN 3
        WHEN 'PROMOTE'         THEN 4
        WHEN 'DELIST'          THEN 5
        ELSE 9
    END AS priority_rank,

    -- Human-readable rationale
    CASE action_type
        WHEN 'RESTOCK_NOW'
            THEN
                COALESCE(abc_class, '?') || '-class'
                || CASE WHEN is_oos THEN ' đã hết hàng' ELSE ' sắp hết hàng' END
                || ' — còn '
                || ROUND(COALESCE(days_of_supply, 0), 0)::INTEGER::VARCHAR
                || ' ngày tồn — nhập gấp'
        WHEN 'CLEAR_DEADSTOCK'
            THEN
                'Hàng chết ' || COALESCE(days_since_last_sale::VARCHAR, '?') || ' ngày không bán'
                || ' — vốn kẹt ~'
                || ROUND(COALESCE(dead_stock_value_at_risk, 0) / 1000000.0, 1)::VARCHAR
                || 'M — thanh lý'
        WHEN 'REVIEW_MARGIN'
            THEN
                CASE
                    WHEN health_class = 'WORKHORSE' AND velocity_momentum = 'DECELERATING'
                        THEN 'WORKHORSE biên đang giảm — kiểm tra giá vốn/đối thủ'
                    WHEN COALESCE(cogs_variance_pct, 0) > 0.20
                        THEN 'Giá vốn biến động >'
                            || ROUND(cogs_variance_pct * 100, 0)::INTEGER::VARCHAR
                            || '% vs 3-tháng — xác minh MISA'
                    ELSE 'Biên margin thấp bất thường — review cogs_source và giá bán'
                END
        WHEN 'PROMOTE'
            THEN
                'Margin cao (' || COALESCE(ROUND(realized_margin_pct, 1)::VARCHAR, '?') || '%)'
                || ' nhưng velocity thấp — đẩy bán/tăng exposure'
        WHEN 'DELIST'
            THEN
                'DOG + chết hàng ' || COALESCE(days_since_last_sale::VARCHAR, '?') || ' ngày'
                || ' — xem xét ngừng kinh doanh'
        ELSE NULL
    END AS action_rationale,

    -- Value at stake: quantifies opportunity cost / capital risk for triage ordering.
    -- All figures in VND.
    CASE action_type
        WHEN 'RESTOCK_NOW'
            -- Estimated lost revenue over 7-day restock lead-time at 90d avg velocity
            THEN ROUND(
                COALESCE(velocity_90d, 0) * 7 * COALESCE(avg_unit_price, 0)
            )::BIGINT
        WHEN 'CLEAR_DEADSTOCK'
            THEN ROUND(COALESCE(dead_stock_value_at_risk, 0))::BIGINT
        WHEN 'REVIEW_MARGIN'
            -- Capital exposed at current stock value (worst-case if margin issue is structural)
            THEN ROUND(COALESCE(stock_value_at_mac, 0))::BIGINT
        WHEN 'PROMOTE'
            -- Revenue upside proxy: 2× monthly units at avg unit price
            THEN ROUND(
                COALESCE(units_sold, 0) * 2 * COALESCE(avg_unit_price, 0)
            )::BIGINT
        WHEN 'DELIST'
            THEN ROUND(COALESCE(dead_stock_value_at_risk, 0))::BIGINT
        ELSE NULL
    END AS value_at_stake,

    -- Raw signals (for dashboard drill-down)
    oos_risk,
    is_oos,
    is_low_stock,
    is_dead_stock,
    on_hand,
    days_of_supply,
    dead_stock_value_at_risk,
    stock_value_at_mac,
    realized_margin_pct,
    cogs_variance_pct,
    velocity_90d,
    days_since_last_sale,
    discount_dependency,

    current_timestamp AS queue_generated_at

FROM classified
WHERE action_type IS NOT NULL
ORDER BY priority_rank, dead_stock_value_at_risk DESC NULLS LAST

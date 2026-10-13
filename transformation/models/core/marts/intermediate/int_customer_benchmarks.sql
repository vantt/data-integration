{{ config(
    materialized='table',
    tags=['mart', 'intermediate']
) }}

-- =============================================================================
-- INT: CUSTOMER BENCHMARKS
-- =============================================================================
-- Percentile rankings and peer-group context for customers eligible for comparison.
-- Grain: one row per customer_key (ALL customers from dim_customers_base).
--
-- Rankable population (n ≈ 939):
--   lifetime_value > 0 AND order_count >= 2
--   AND customer_type = 'RETAIL'
--   AND COALESCE(acquisition_source, '') <> 'Đại Lý'
--
-- Materialized as TABLE (not incremental) because:
--   - PERCENT_RANK() is a whole-population window — every row affects every percentile.
--   - An incremental run that recomputes only changed rows would silently corrupt
--     percentile values for unchanged rows when the population shifts.
--   - Rebuild cost is small (≤ 939 ranked rows, ~7k total).
--
-- v1 metrics (YAGNI — extend only when sales explicitly needs more):
--   metric_1: lifetime_value (monetary CLV)
--   metric_2: clv_per_active_month = lifetime_value / GREATEST(lifespan_days / 30, 1)
--             tenure-normalised CLV so new high-value customers are not penalised
--
-- v1 frames (YAGNI):
--   frame_1: all_rankable   — all 939 repeat-buyer RETAIL customers
--   frame_2: in_value_group — same value_group bucket (min-group guard: n < 30 → fallback)
--
-- Output per metric × frame:
--   *_pct      — ROUND(PERCENT_RANK() * 100, 1)  → [0.0 .. 100.0]
--   *_bucket   — top_5pct | top_decile | top_quartile | above_median | below_median
--   *_phrase   — ready-made Vietnamese phrase for LLM verbalization (no raw numbers exposed)
--   *_frame_used — which frame was actually used after min-group fallback

WITH base AS (
    -- Pull everything needed from dim_customers (external parquet read at dbt runtime).
    -- dim_customers is built BEFORE this model in the DAG (int_customer_benchmarks
    -- is referenced only by dim_customers itself via LEFT JOIN, so no circular dep —
    -- dim_customers reads from int_customer_benchmarks at JOIN time, not as a ref()).
    -- We ref dim_customers_base + int_customer_metrics to avoid circular dependency.
    SELECT
        c.customer_key,
        -- customer_type logic mirrors dim_customers.sql exactly (no circular dep)
        CASE
            WHEN c.customer_group LIKE '%WHOLESALE%' THEN 'WHOLESALE'
            WHEN c.customer_group LIKE '%TYPE_PARTNER%' OR c.customer_group LIKE '%KY_GUI%' THEN 'PARTNER'
            WHEN c.customer_group LIKE '%TYPE_STAFF%' THEN 'STAFF'
            WHEN c.customer_group LIKE '%TYPE_KOL%' THEN 'KOL'
            WHEN c.customer_group LIKE '%TYPE_CROSSBORDER%' OR c.customer_group LIKE '%CTN00014%' THEN 'CROSSBORDER'
            ELSE 'RETAIL'
        END AS customer_type,
        -- value_group mirrors dim_customers.sql (needed for in_value_group frame)
        CASE
            WHEN COALESCE(m.monetary_value, 0) >= 50000000 OR COALESCE(m.frequency, 0) >= 20 THEN 'VALUE_VIP'
            WHEN COALESCE(m.monetary_value, 0) >= 20000000 THEN 'VALUE_GOLD'
            WHEN COALESCE(m.monetary_value, 0) >= 5000000  THEN 'VALUE_SILVER'
            ELSE 'VALUE_BRONZE'
        END AS value_group,
        COALESCE(m.monetary_value, 0)         AS lifetime_value,
        COALESCE(m.frequency, 0)              AS order_count,
        m.lifespan_days,
        m.acquisition_source
    FROM {{ ref('dim_customers_base') }} c
    LEFT JOIN {{ ref('int_customer_metrics') }} m ON c.customer_key = m.customer_key
),

-- Classify every customer into benchmark_status before computing any window functions.
-- This determines who enters the ranked population and who gets a descriptive label.
status_flags AS (
    SELECT
        *,
        CASE
            WHEN customer_type NOT IN ('RETAIL') THEN 'non_retail'
            WHEN lifetime_value <= 0             THEN 'inactive_zero_value'
            WHEN order_count < 2                 THEN 'single_purchase'
            WHEN COALESCE(acquisition_source, '') = 'Đại Lý' THEN 'non_retail'
            ELSE 'ranked'
        END AS benchmark_status,
        -- Tenure-normalised CLV: divides by active months (floor at 1 to avoid /0 for new customers)
        lifetime_value / GREATEST(COALESCE(lifespan_days, 0) / 30.0, 1.0) AS clv_per_active_month
    FROM base
),

-- Rankable population only — used for all_rankable frame windows
rankable AS (
    SELECT * FROM status_flags WHERE benchmark_status = 'ranked'
),

-- Count customers per value_group within the rankable population.
-- Used to enforce min-group guard (n < 30 → fallback to all_rankable frame).
value_group_counts AS (
    SELECT
        value_group,
        COUNT(*) AS vg_count
    FROM rankable
    GROUP BY value_group
),

-- Compute population-level statistics on the rankable set.
-- median (PERCENTILE_CONT 0.5) is robust to outliers (vs mean which is skewed by whales).
rankable_stats AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lifetime_value) AS median_lifetime_value
    FROM rankable
),

-- Window functions for all_rankable frame.
-- PERCENT_RANK() returns [0,1]; multiply by 100 and round to 1 dp → [0.0, 100.0].
-- Lower percentile = lower spend relative to peers (0 = lowest, 100 = highest).
all_rankable_windows AS (
    SELECT
        customer_key,
        ROUND(PERCENT_RANK() OVER (ORDER BY lifetime_value)        * 100, 1) AS lv_all_pct,
        ROUND(PERCENT_RANK() OVER (ORDER BY clv_per_active_month)  * 100, 1) AS clv_all_pct
    FROM rankable
),

-- Window functions for in_value_group frame.
-- Separate PARTITION BY value_group window; fallback handled later.
vg_windows AS (
    SELECT
        customer_key,
        value_group,
        ROUND(PERCENT_RANK() OVER (PARTITION BY value_group ORDER BY lifetime_value)       * 100, 1) AS lv_vg_pct,
        ROUND(PERCENT_RANK() OVER (PARTITION BY value_group ORDER BY clv_per_active_month) * 100, 1) AS clv_vg_pct
    FROM rankable
),

-- Assemble all ranked rows with both frames and apply min-group fallback.
ranked_combined AS (
    SELECT
        r.customer_key,
        r.lifetime_value,
        r.clv_per_active_month,
        r.value_group,

        -- all_rankable frame (always available for ranked rows)
        a.lv_all_pct,
        a.clv_all_pct,

        -- in_value_group frame with fallback
        -- If the customer's value_group has < 30 ranked members, the within-group
        -- percentile is meaningless — fall back to all_rankable and record it.
        CASE
            WHEN COALESCE(vgc.vg_count, 0) >= 30 THEN v.lv_vg_pct
            ELSE a.lv_all_pct
        END AS lv_vg_pct_effective,

        CASE
            WHEN COALESCE(vgc.vg_count, 0) >= 30 THEN v.clv_vg_pct
            ELSE a.clv_all_pct
        END AS clv_vg_pct_effective,

        CASE
            WHEN COALESCE(vgc.vg_count, 0) >= 30 THEN 'in_value_group'
            ELSE 'all_rankable_fallback'
        END AS lv_vg_frame_used,

        CASE
            WHEN COALESCE(vgc.vg_count, 0) >= 30 THEN 'in_value_group'
            ELSE 'all_rankable_fallback'
        END AS clv_vg_frame_used,

        s.median_lifetime_value
    FROM rankable r
    JOIN all_rankable_windows  a   ON r.customer_key = a.customer_key
    JOIN vg_windows            v   ON r.customer_key = v.customer_key
    JOIN value_group_counts    vgc ON r.value_group  = vgc.value_group
    CROSS JOIN rankable_stats  s
),

-- Bucket assignment macro-logic (inline, no UDF needed):
--   > 95 → top_5pct
--   > 90 → top_decile
--   > 75 → top_quartile
--   > 50 → above_median
--   else → below_median
-- Applied to all 4 metric×frame combinations.
bucketed AS (
    SELECT
        customer_key,
        lifetime_value,
        clv_per_active_month,
        value_group,
        median_lifetime_value,

        -- Ratio vs population median (robust outlier-safe denominator)
        ROUND(lifetime_value / NULLIF(median_lifetime_value, 0), 2) AS clv_vs_rankable_median,

        -- === metric: lifetime_value × frame: all_rankable ===
        lv_all_pct                   AS lv_all_rankable_pct,
        CASE
            WHEN lv_all_pct > 95 THEN 'top_5pct'
            WHEN lv_all_pct > 90 THEN 'top_decile'
            WHEN lv_all_pct > 75 THEN 'top_quartile'
            WHEN lv_all_pct > 50 THEN 'above_median'
            ELSE 'below_median'
        END                          AS lv_all_rankable_bucket,
        CASE
            WHEN lv_all_pct > 95 THEN 'thuộc nhóm ~5% chi tiêu cao nhất trong khách mua lặp lại'
            WHEN lv_all_pct > 90 THEN 'thuộc nhóm ~10% chi tiêu cao nhất trong khách mua lặp lại'
            WHEN lv_all_pct > 75 THEN 'thuộc nhóm 25% chi tiêu cao nhất trong khách mua lặp lại'
            WHEN lv_all_pct > 50 THEN 'chi tiêu trên mức trung vị trong khách mua lặp lại'
            ELSE 'chi tiêu dưới mức trung vị trong khách mua lặp lại'
        END                          AS lv_all_rankable_phrase,

        -- === metric: lifetime_value × frame: in_value_group ===
        lv_vg_pct_effective          AS lv_in_value_group_pct,
        CASE
            WHEN lv_vg_pct_effective > 95 THEN 'top_5pct'
            WHEN lv_vg_pct_effective > 90 THEN 'top_decile'
            WHEN lv_vg_pct_effective > 75 THEN 'top_quartile'
            WHEN lv_vg_pct_effective > 50 THEN 'above_median'
            ELSE 'below_median'
        END                          AS lv_in_value_group_bucket,
        CASE
            WHEN lv_vg_pct_effective > 95 THEN 'thuộc nhóm ~5% chi tiêu cao nhất trong cùng phân khúc khách hàng'
            WHEN lv_vg_pct_effective > 90 THEN 'thuộc nhóm ~10% chi tiêu cao nhất trong cùng phân khúc khách hàng'
            WHEN lv_vg_pct_effective > 75 THEN 'thuộc nhóm 25% chi tiêu cao nhất trong cùng phân khúc khách hàng'
            WHEN lv_vg_pct_effective > 50 THEN 'chi tiêu trên mức trung vị trong cùng phân khúc khách hàng'
            ELSE 'chi tiêu dưới mức trung vị trong cùng phân khúc khách hàng'
        END                          AS lv_in_value_group_phrase,
        lv_vg_frame_used,

        -- === metric: clv_per_active_month × frame: all_rankable ===
        clv_all_pct                  AS clv_all_rankable_pct,
        CASE
            WHEN clv_all_pct > 95 THEN 'top_5pct'
            WHEN clv_all_pct > 90 THEN 'top_decile'
            WHEN clv_all_pct > 75 THEN 'top_quartile'
            WHEN clv_all_pct > 50 THEN 'above_median'
            ELSE 'below_median'
        END                          AS clv_all_rankable_bucket,
        CASE
            WHEN clv_all_pct > 95 THEN 'thuộc nhóm ~5% chi tiêu hiệu quả nhất theo thời gian gắn bó trong khách mua lặp lại'
            WHEN clv_all_pct > 90 THEN 'thuộc nhóm ~10% chi tiêu hiệu quả nhất theo thời gian gắn bó trong khách mua lặp lại'
            WHEN clv_all_pct > 75 THEN 'thuộc nhóm 25% chi tiêu hiệu quả nhất theo thời gian gắn bó trong khách mua lặp lại'
            WHEN clv_all_pct > 50 THEN 'chi tiêu theo thời gian gắn bó trên mức trung vị trong khách mua lặp lại'
            ELSE 'chi tiêu theo thời gian gắn bó dưới mức trung vị trong khách mua lặp lại'
        END                          AS clv_all_rankable_phrase,

        -- === metric: clv_per_active_month × frame: in_value_group ===
        clv_vg_pct_effective         AS clv_in_value_group_pct,
        CASE
            WHEN clv_vg_pct_effective > 95 THEN 'top_5pct'
            WHEN clv_vg_pct_effective > 90 THEN 'top_decile'
            WHEN clv_vg_pct_effective > 75 THEN 'top_quartile'
            WHEN clv_vg_pct_effective > 50 THEN 'above_median'
            ELSE 'below_median'
        END                          AS clv_in_value_group_bucket,
        CASE
            WHEN clv_vg_pct_effective > 95 THEN 'thuộc nhóm ~5% chi tiêu hiệu quả nhất theo thời gian gắn bó trong cùng phân khúc'
            WHEN clv_vg_pct_effective > 90 THEN 'thuộc nhóm ~10% chi tiêu hiệu quả nhất theo thời gian gắn bó trong cùng phân khúc'
            WHEN clv_vg_pct_effective > 75 THEN 'thuộc nhóm 25% chi tiêu hiệu quả nhất theo thời gian gắn bó trong cùng phân khúc'
            WHEN clv_vg_pct_effective > 50 THEN 'chi tiêu theo thời gian gắn bó trên mức trung vị trong cùng phân khúc'
            ELSE 'chi tiêu theo thời gian gắn bó dưới mức trung vị trong cùng phân khúc'
        END                          AS clv_in_value_group_phrase,
        clv_vg_frame_used

    FROM ranked_combined
)

-- Final output: union ranked rows (with percentiles) + non-ranked rows (with status only).
-- Non-ranked rows get NULL for all percentile columns — status flag tells the consumer why.
SELECT
    sf.customer_key,
    sf.benchmark_status,
    sf.lifetime_value,
    sf.clv_per_active_month,
    sf.value_group,

    -- Percentile columns: NULL for non-ranked customers
    b.lv_all_rankable_pct,
    b.lv_all_rankable_bucket,
    b.lv_all_rankable_phrase,

    b.lv_in_value_group_pct,
    b.lv_in_value_group_bucket,
    b.lv_in_value_group_phrase,
    b.lv_vg_frame_used,

    b.clv_all_rankable_pct,
    b.clv_all_rankable_bucket,
    b.clv_all_rankable_phrase,

    b.clv_in_value_group_pct,
    b.clv_in_value_group_bucket,
    b.clv_in_value_group_phrase,
    b.clv_vg_frame_used,

    -- Population-relative ratio: "X times median repeat-buyer spend"
    -- NULL for non-ranked customers
    b.clv_vs_rankable_median

FROM status_flags sf
LEFT JOIN bucketed b ON sf.customer_key = b.customer_key

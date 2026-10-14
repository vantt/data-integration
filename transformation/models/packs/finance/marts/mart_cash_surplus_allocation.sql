{{ config(
    tags=['mart', 'finance', 'budget', 'allocation'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CASH SURPLUS ALLOCATION (Waterfall)
-- =================================================================================================
-- Grain: 1 row per (period_month, bucket).
-- Algorithm: apply policy rules in priority order to closing_balance surplus.
--   1. fill_to_target  → fill bucket until value VND total; allocated = min(free, gap_to_target)
--   2. fixed           → allocate exactly value VND; allocated = min(free, value)
--   3. pct_remaining   → allocate value% of remaining free cash
--   4. from_plan       → allocate Σ planned outflow for that bucket from fact_cashflow_budget
--   5. remainder       → all remaining free cash (must be last priority)
-- free_cash = closing_balance − Σ allocated so far
-- materialized=table: MUST NOT use incremental — policy changes affect past periods.
-- =================================================================================================

WITH monthly_balance AS (
    -- Closing cash balance per month (all 111x/112x)
    SELECT
        period_month,
        SUM(closing_balance) AS closing_balance
    FROM {{ ref('fact_account_balance_monthly') }}
    WHERE account_code LIKE '111%' OR account_code LIKE '112%'
    GROUP BY 1
),

reserve_gaps AS (
    -- Total gap remaining across all reserve items (used for fill_to_target denominator)
    SELECT
        last_period                             AS period_month,
        SUM(gap_remaining)                      AS total_reserve_gap
    FROM {{ ref('mart_cashflow_reserve_status') }}
    WHERE gap_remaining > 0
    GROUP BY 1
),

period_policy AS (
    -- Effective policy for each month (join effective-date window)
    SELECT
        mb.period_month,
        mb.closing_balance,
        p.priority,
        p.bucket,
        p.rule_type,
        p.value
    FROM monthly_balance mb
    JOIN {{ ref('dim_cash_allocation_policy') }} p
        ON  p.effective_from <= mb.period_month
        AND (p.effective_to IS NULL OR p.effective_to >= mb.period_month)
),

budget_by_bucket AS (
    -- Σ planned outflow per (period_month, bucket=cashflow_line) for from_plan rule
    SELECT period_month, cashflow_line AS bucket, SUM(planned_amount) AS planned_outflow
    FROM {{ ref('fact_cashflow_budget') }}
    WHERE direction = 'outflow'
    GROUP BY 1, 2
),

allocated AS (
    -- Apply waterfall in priority order using window function running sum
    SELECT
        pp.period_month,
        pp.closing_balance,
        pp.priority,
        pp.bucket,
        pp.rule_type,
        pp.value,
        COALESCE(bb.planned_outflow, 0)         AS bucket_plan,

        -- Running sum of previously allocated (higher-priority buckets)
        SUM(
            CASE pp.rule_type
                WHEN 'fixed'          THEN LEAST(GREATEST(pp.closing_balance - 0, 0), pp.value)
                WHEN 'pct_remaining'  THEN GREATEST(pp.closing_balance - 0, 0) * pp.value / 100.0
                WHEN 'from_plan'      THEN COALESCE(bb.planned_outflow, 0)
                ELSE 0
            END
        ) OVER (
            PARTITION BY pp.period_month
            ORDER BY pp.priority
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        )                                       AS already_allocated,

        pp.closing_balance AS cb
    FROM period_policy pp
    LEFT JOIN budget_by_bucket bb
        ON  bb.period_month = pp.period_month
        AND bb.bucket       = pp.bucket
)

SELECT
    period_month,
    bucket,
    rule_type,
    priority,
    CAST(closing_balance AS BIGINT)     AS closing_balance,
    CAST(
        CASE rule_type
            WHEN 'fill_to_target' THEN LEAST(GREATEST(closing_balance - COALESCE(already_allocated,0), 0), COALESCE(value,0))
            WHEN 'fixed'          THEN LEAST(GREATEST(closing_balance - COALESCE(already_allocated,0), 0), COALESCE(value,0))
            WHEN 'pct_remaining'  THEN GREATEST(closing_balance - COALESCE(already_allocated,0), 0) * COALESCE(value,0) / 100.0
            WHEN 'from_plan'      THEN LEAST(GREATEST(closing_balance - COALESCE(already_allocated,0), 0), bucket_plan)
            WHEN 'remainder'      THEN GREATEST(closing_balance - COALESCE(already_allocated,0), 0)
            ELSE 0
        END AS BIGINT
    )                                   AS allocated_amount,
    CAST(COALESCE(already_allocated, 0) AS BIGINT) AS previously_allocated,
    current_timestamp                   AS loaded_at

FROM allocated
ORDER BY period_month, priority

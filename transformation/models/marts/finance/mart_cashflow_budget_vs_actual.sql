{{ config(
    tags=['mart', 'finance', 'budget', 'report'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CASHFLOW BUDGET vs ACTUAL
-- =================================================================================================
-- Grain: 1 row per (cashflow_line, period_month, direction).
-- FULL OUTER JOIN: budget-only = future periods; actual-only = lines without budget.
-- variance_amount = actual − plan (+ve = over-collected for inflow / overspent for outflow).
-- attainment_pct  = actual / plan * 100 (pace within period).
-- =================================================================================================

WITH budget AS (
    SELECT cashflow_line, period_month, direction, SUM(planned_amount) AS planned_amount
    FROM {{ ref('fact_cashflow_budget') }}
    GROUP BY 1, 2, 3
),

actual AS (
    SELECT
        cashflow_line,
        period_month,
        direction,
        SUM(amount) AS actual_amount
    FROM {{ ref('fact_cash_movement') }}
    WHERE NOT is_internal_transfer
      AND cashflow_line IS NOT NULL
      AND cashflow_line NOT IN ('Chuyển nội bộ tiền', 'Khác')
    GROUP BY 1, 2, 3
),

joined AS (
    SELECT
        COALESCE(b.cashflow_line, a.cashflow_line) AS cashflow_line,
        COALESCE(b.period_month,  a.period_month)  AS period_month,
        COALESCE(b.direction,     a.direction)      AS direction,
        COALESCE(b.planned_amount, 0)               AS planned_amount,
        COALESCE(a.actual_amount,  0)               AS actual_amount,
        CASE
            WHEN b.cashflow_line IS NULL THEN 'actual_only'
            WHEN a.cashflow_line IS NULL THEN 'budget_only'
            ELSE 'both'
        END AS coverage
    FROM budget b
    FULL OUTER JOIN actual a
        ON  a.cashflow_line = b.cashflow_line
        AND a.period_month  = b.period_month
        AND a.direction     = b.direction
)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'cashflow_line',
        'CAST(period_month AS VARCHAR)',
        'direction'
    ]) }}                                               AS bva_key,

    cashflow_line,
    period_month,
    direction,
    CAST(planned_amount AS BIGINT)                      AS planned_amount,
    CAST(actual_amount  AS BIGINT)                      AS actual_amount,
    CAST(actual_amount - planned_amount AS BIGINT)      AS variance_amount,
    ROUND(
        (actual_amount - planned_amount) * 100.0
        / NULLIF(planned_amount, 0), 1
    )                                                   AS variance_pct,
    ROUND(
        actual_amount * 100.0 / NULLIF(planned_amount, 0), 1
    )                                                   AS attainment_pct,
    coverage,
    current_timestamp                                   AS loaded_at

FROM joined

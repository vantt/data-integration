{{ config(
    tags=['mart', 'finance', 'budget', 'report'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CASHFLOW BUDGET vs ACTUAL
-- =================================================================================================
-- Grain: 1 row per (COALESCE(account_code, cashflow_line), period_month, direction).
-- FULL OUTER JOIN: budget-only = future periods; actual-only = lines without budget.
-- variance_amount = actual − plan (+ve = over-collected for inflow / overspent for outflow).
-- attainment_pct  = actual / plan * 100 (pace within period).
--
-- Join key transition (see plans/260709-1415-budget-account-level-remap/):
--   budget.account_code populated  -> prefix-match against actual.account_code (offset_account).
--                                     Supports both parent-level budgeting (rolls up every child
--                                     account) and child-level budgeting (exact leaf match).
--   budget.account_code empty      -> legacy exact-match on cashflow_line (pre-migration rows).
-- A budget row must never match via BOTH paths at once — mutual-exclusivity (cha/con collision)
-- is enforced upstream at sync time (phase-03), not here; this mart only joins.
-- =================================================================================================

WITH budget AS (
    -- one_off/reserve are plan-side sinking funds ("để dành, khi nào đủ thì dùng") — they
    -- never join to a MISA actuals line, so they're excluded from variance. They still
    -- count in mart_cashflow_forecast (real outflow) and Tab B reserve tracking.
    SELECT
        cashflow_line,
        account_code,
        period_month,
        direction,
        SUM(planned_amount) AS planned_amount
    FROM {{ ref('fact_cashflow_budget') }}
    WHERE item_type = 'recurring'
    GROUP BY 1, 2, 3, 4
),

actual AS (
    SELECT
        offset_account AS account_code,
        cashflow_line,
        period_month,
        direction,
        SUM(amount) AS actual_amount
    FROM {{ ref('fact_cash_movement') }}
    WHERE NOT is_internal_transfer
      AND cashflow_line IS NOT NULL
      AND cashflow_line NOT IN ('Chuyển nội bộ tiền', 'Khác')
    GROUP BY 1, 2, 3, 4
),

joined AS (
    -- A cha-level budget row (account_code = parent) can match MULTIPLE leaf actual rows
    -- (rollup) -> 1 budget row joins N actual rows here. Do not read planned/actual off
    -- this CTE directly; the `grouped` CTE below collapses the duplication correctly.
    SELECT
        COALESCE(b.account_code, a.account_code)   AS account_code,
        COALESCE(b.cashflow_line, a.cashflow_line) AS cashflow_line,
        COALESCE(b.period_month,  a.period_month)  AS period_month,
        COALESCE(b.direction,     a.direction)      AS direction,
        b.planned_amount,
        a.actual_amount
    FROM budget b
    FULL OUTER JOIN actual a
        ON  a.period_month  = b.period_month
        AND a.direction     = b.direction
        AND (
              (b.account_code IS NOT NULL
               AND (a.account_code = b.account_code OR a.account_code LIKE b.account_code || '%'))
           OR (b.account_code IS NULL AND a.cashflow_line = b.cashflow_line)
        )
),

grouped AS (
    -- Collapse the cha-rollup duplication: planned_amount is identical across every
    -- duplicated row for a given budget row (MAX just de-dupes, not a real aggregation);
    -- actual_amount is legitimately additive across the matched children (SUM).
    SELECT
        COALESCE(account_code, cashflow_line) AS grain_key,
        MAX(cashflow_line)   AS cashflow_line,
        MAX(account_code)    AS account_code,
        period_month,
        direction,
        MAX(planned_amount)  AS planned_amount,
        SUM(actual_amount)   AS actual_amount,
        CASE
            WHEN MAX(planned_amount) IS NULL THEN 'actual_only'
            WHEN SUM(actual_amount)  IS NULL THEN 'budget_only'
            ELSE 'both'
        END AS coverage
    FROM joined
    GROUP BY COALESCE(account_code, cashflow_line), period_month, direction
)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'COALESCE(account_code, cashflow_line)',
        'CAST(period_month AS VARCHAR)',
        'direction'
    ]) }}                                               AS bva_key,

    account_code,
    cashflow_line,
    period_month,
    direction,
    CAST(COALESCE(planned_amount, 0) AS BIGINT)         AS planned_amount,
    CAST(COALESCE(actual_amount, 0)  AS BIGINT)         AS actual_amount,
    CAST(COALESCE(actual_amount, 0) - COALESCE(planned_amount, 0) AS BIGINT) AS variance_amount,
    ROUND(
        (COALESCE(actual_amount, 0) - COALESCE(planned_amount, 0)) * 100.0
        / NULLIF(planned_amount, 0), 1
    )                                                   AS variance_pct,
    ROUND(
        COALESCE(actual_amount, 0) * 100.0 / NULLIF(planned_amount, 0), 1
    )                                                   AS attainment_pct,
    coverage,
    current_timestamp                                   AS loaded_at

FROM grouped

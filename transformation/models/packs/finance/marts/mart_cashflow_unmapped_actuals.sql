{{ config(
    tags=['mart', 'finance', 'budget', 'report'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CASHFLOW UNMAPPED ACTUALS (orphan report)
-- =================================================================================================
-- Grain: 1 row per (account_code, period_month, direction).
-- Actuals from fact_cash_movement that don't match ANY recurring budget row (neither via
-- account_code prefix-match nor the legacy cashflow_line fallback) — surfaced here instead of
-- silently vanishing or bleeding into some other line's variance. See plans/260709-1415-budget-
-- account-level-remap/plan.md §Khó khăn #1: no auto-classification of WHY a dollar is unmapped
-- (expected reserve/one_off spend vs a genuine recurring gap) — that judgment stays with finance,
-- reviewed monthly. This mart is a safety net, not a final answer.
--
-- Join logic mirrors mart_cashflow_budget_vs_actual's `joined` CTE exactly (same prefix-match +
-- legacy-fallback condition) so the two marts are true complements — every fact_cash_movement
-- dollar (excluding real internal transfers) lands in exactly one of the two, never both, never
-- neither. Deliberately does NOT apply mart_cashflow_budget_vs_actual's extra
-- `cashflow_line NOT IN ('Chuyển nội bộ tiền', 'Khác')` filter — those are exactly the
-- unclassified/catch-all actuals this report exists to catch, not hide.
-- =================================================================================================

WITH budget AS (
    SELECT cashflow_line, account_code, period_month, direction
    FROM {{ ref('fact_cashflow_budget') }}
    WHERE item_type = 'recurring'
),

actual AS (
    SELECT
        offset_account AS account_code,
        cashflow_line,
        period_month,
        direction,
        SUM(amount) AS amount
    FROM {{ ref('fact_cash_movement') }}
    WHERE NOT is_internal_transfer
      AND offset_account IS NOT NULL
    GROUP BY 1, 2, 3, 4
),

unmatched AS (
    SELECT a.*
    FROM actual a
    WHERE NOT EXISTS (
        SELECT 1
        FROM budget b
        WHERE b.period_month = a.period_month
          AND b.direction    = a.direction
          AND (
                (b.account_code IS NOT NULL
                 AND (a.account_code = b.account_code OR a.account_code LIKE b.account_code || '%'))
             OR (b.account_code IS NULL AND a.cashflow_line = b.cashflow_line)
          )
    )
)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'u.account_code',
        'CAST(u.period_month AS VARCHAR)',
        'u.direction'
    ]) }}                                AS unmapped_actual_key,

    u.account_code,
    ga.account_name,
    u.cashflow_line,
    u.period_month,
    u.direction,
    CAST(u.amount AS BIGINT)             AS amount,
    current_timestamp                    AS loaded_at

FROM unmatched u
LEFT JOIN {{ ref('dim_gl_account') }} ga ON ga.account_code = u.account_code

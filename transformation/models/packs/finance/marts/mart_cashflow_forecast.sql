{{ config(
    tags=['mart', 'finance', 'budget', 'forecast'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CASH BALANCE FORECAST (dự báo số dư quỹ)
-- =================================================================================================
-- Algorithm:
--   anchor = closing balance of latest complete month (all 111x/112x accounts combined)
--   for each FUTURE period_month in fact_cashflow_budget:
--     planned_net_flow(m)  = Σ planned_inflow(m) − Σ planned_outflow(m)
--     projected_balance(m) = anchor + Σ planned_net_flow(anchor+1 .. m)
--
-- row_type:
--   'actual'   → past: actual_balance from fact_account_balance_monthly (solid line)
--   'forecast' → future: projected_balance (dashed line)
-- =================================================================================================

WITH balance_monthly AS (
    SELECT
        period_month,
        SUM(closing_balance) AS actual_closing_balance
    FROM {{ ref('fact_account_balance_monthly') }}
    WHERE account_code LIKE '111%' OR account_code LIKE '112%'
    GROUP BY 1
),

anchor AS (
    SELECT period_month AS anchor_month, actual_closing_balance AS anchor_balance
    FROM balance_monthly
    ORDER BY period_month DESC
    LIMIT 1
),

future_budget AS (
    SELECT
        b.period_month,
        SUM(CASE WHEN b.direction = 'inflow'  THEN  b.planned_amount ELSE 0 END) AS planned_inflow,
        SUM(CASE WHEN b.direction = 'outflow' THEN  b.planned_amount ELSE 0 END) AS planned_outflow,
        SUM(CASE WHEN b.direction = 'inflow'  THEN  b.planned_amount
                 WHEN b.direction = 'outflow' THEN -b.planned_amount
                 ELSE 0 END)                                                     AS planned_net_flow
    FROM {{ ref('fact_cashflow_budget') }} b
    CROSS JOIN anchor a
    WHERE b.period_month > a.anchor_month
      AND b.cashflow_line NOT IN ('Chuyển nội bộ tiền', 'Khác')
    GROUP BY 1
),

forecast_cumulative AS (
    SELECT
        period_month,
        planned_inflow,
        planned_outflow,
        planned_net_flow,
        SUM(planned_net_flow) OVER (
            ORDER BY period_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_net_flow
    FROM future_budget
)

SELECT
    b.period_month,
    CAST(b.actual_closing_balance AS BIGINT) AS actual_balance,
    NULL::BIGINT                             AS planned_inflow,
    NULL::BIGINT                             AS planned_outflow,
    NULL::BIGINT                             AS planned_net_flow,
    NULL::BIGINT                             AS projected_balance,
    'actual'                                 AS row_type
FROM balance_monthly b

UNION ALL

SELECT
    fc.period_month,
    NULL::BIGINT                                               AS actual_balance,
    CAST(fc.planned_inflow   AS BIGINT)                       AS planned_inflow,
    CAST(fc.planned_outflow  AS BIGINT)                       AS planned_outflow,
    CAST(fc.planned_net_flow AS BIGINT)                       AS planned_net_flow,
    CAST(a.anchor_balance + fc.cumulative_net_flow AS BIGINT) AS projected_balance,
    'forecast'                                                 AS row_type
FROM forecast_cumulative fc
CROSS JOIN anchor a

ORDER BY period_month

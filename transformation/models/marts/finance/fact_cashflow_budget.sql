{{ config(
    tags=['mart', 'fact', 'finance', 'budget'],
    location="{{ get_rolling_location() }}"
) }}

-- Grain: 1 row per (cashflow_line, period_month, direction, item_type, item_label).
-- Source: seed_cashflow_budget — generated from Google Sheet tab BUDGET_ITEMS.
-- Single source by design (MISA budget module dropped). No priority ranking needed.

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'cashflow_line',
        'CAST(period_month AS VARCHAR)',
        'direction',
        'COALESCE(item_label, cashflow_line)'
    ]) }}                                   AS cashflow_budget_key,

    s.cashflow_line,
    NULLIF(s.account_code, '')              AS account_code,
    CAST(s.period_month AS DATE)            AS period_month,
    s.direction,
    CAST(s.planned_amount AS BIGINT)        AS planned_amount,
    s.payment_week,
    s.item_type,
    s.item_label,
    CAST(s.item_target AS BIGINT)           AS item_target,
    CAST(s.target_month AS DATE)            AS target_month,
    s.notes,
    current_timestamp                       AS loaded_at

FROM {{ ref('seed_cashflow_budget') }} s
WHERE cashflow_line IS NOT NULL
  AND period_month IS NOT NULL
  AND direction IN ('inflow', 'outflow')
  AND planned_amount >= 0
  AND item_type IN ('recurring', 'one_off', 'reserve')

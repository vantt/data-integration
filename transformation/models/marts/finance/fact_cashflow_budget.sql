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

    cashflow_line,
    CAST(period_month AS DATE)              AS period_month,
    direction,
    CAST(planned_amount AS BIGINT)          AS planned_amount,
    payment_week,
    item_type,
    item_label,
    CAST(item_target AS BIGINT)             AS item_target,
    CAST(target_month AS DATE)              AS target_month,
    notes,
    current_timestamp                       AS loaded_at

FROM {{ ref('seed_cashflow_budget') }}
WHERE cashflow_line IS NOT NULL
  AND period_month IS NOT NULL
  AND direction IN ('inflow', 'outflow')
  AND planned_amount >= 0
  AND item_type IN ('recurring', 'one_off', 'reserve')

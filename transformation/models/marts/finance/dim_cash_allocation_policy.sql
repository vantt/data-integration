{{ config(
    tags=['mart', 'dim', 'finance', 'budget'],
    location="{{ get_rolling_location() }}"
) }}

-- Dimension: Cash Waterfall Allocation Policy.
-- Grain: 1 row per (priority, bucket, effective_from).
-- Append-only source: effective_to IS NULL = current policy row.
-- Mart join pattern: WHERE effective_from <= period_month AND (effective_to IS NULL OR effective_to >= period_month)

SELECT
    priority,
    bucket,
    rule_type,
    CAST(value AS BIGINT)               AS value,
    CAST(effective_from AS DATE)        AS effective_from,
    CAST(effective_to AS DATE)          AS effective_to,
    notes,
    current_timestamp                   AS loaded_at
FROM {{ ref('seed_cash_allocation_policy') }}
WHERE rule_type IN ('fill_to_target', 'from_plan', 'fixed', 'pct_remaining', 'remainder')
ORDER BY priority

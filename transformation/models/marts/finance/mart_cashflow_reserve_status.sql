{{ config(
    tags=['mart', 'finance', 'budget', 'reserve'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- MART: CASHFLOW RESERVE STATUS
-- =================================================================================================
-- Grain: 1 row per reserve item (cashflow_line + item_label).
-- Purpose: track sinking fund progress — how much planned so far vs target vs gap.
-- Feeds: B2 Reserve Status card (progress bars per item).
-- =================================================================================================

WITH reserve_items AS (
    -- All reserve-type budget items, aggregated across periods (accumulated plan so far)
    SELECT
        cashflow_line,
        COALESCE(item_label, cashflow_line)     AS item_label,
        direction,
        MAX(item_target)                        AS item_target,
        MAX(target_month)                       AS target_month,
        SUM(planned_amount)                     AS accumulated_plan,
        COUNT(DISTINCT period_month)            AS periods_planned,
        MIN(period_month)                       AS first_period,
        MAX(period_month)                       AS last_period
    FROM {{ ref('fact_cashflow_budget') }}
    WHERE item_type = 'reserve'
    GROUP BY 1, 2, 3
)

SELECT
    cashflow_line,
    item_label,
    direction,
    CAST(item_target       AS BIGINT)           AS item_target,
    target_month,
    CAST(accumulated_plan  AS BIGINT)           AS accumulated_plan,
    periods_planned,
    first_period,
    last_period,

    -- Progress metrics (NULL-safe when item_target is NULL = open-ended reserve)
    ROUND(
        accumulated_plan * 100.0 / NULLIF(item_target, 0), 1
    )                                           AS pct_done,

    CAST(
        GREATEST(COALESCE(item_target, 0) - accumulated_plan, 0) AS BIGINT
    )                                           AS gap_remaining,

    -- Monthly adjustment needed: gap / months remaining until target (NULL if no deadline)
    CASE
        WHEN target_month IS NULL OR item_target IS NULL THEN NULL
        ELSE CAST(
            GREATEST(item_target - accumulated_plan, 0)
            / NULLIF(
                -- months from last planned period to target_month
                DATEDIFF('month', last_period, target_month),
                0
            ) AS BIGINT
        )
    END                                         AS required_monthly_adj,

    current_timestamp                           AS loaded_at

FROM reserve_items

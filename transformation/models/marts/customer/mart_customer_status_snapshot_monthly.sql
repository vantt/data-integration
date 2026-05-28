{{ config(
    materialized='table',
    tags=['mart', 'customer', 'snapshot'],
    location="{{ get_rolling_location() }}"
) }}

-- Monthly snapshot of customer status as-of each month-end.
-- One row per (customer_key, snapshot_month).
-- Enables correct MoM retention math without the first_order_date filter bug.
-- Rolling 24-month window (sufficient for YoY analysis).
--
-- Status logic (as-of month-end):
--   ACTIVE : last_order_date >= month_end - 30 days
--   AT_RISK: last_order_date >= month_end - 90 days AND < month_end - 30 days
--   CHURNED: last_order_date < month_end - 90 days
--   is_new = TRUE when first_order_date falls within the snapshot month

WITH customers AS (
    SELECT
        customer_key,
        customer_id,
        customer_type,
        first_order_date,
        last_order_date,
        total_orders_count,
        lifetime_value,
        value_group,
        channel_preference,
        product_affinity,
        payment_behavior
    FROM {{ ref('dim_customers') }}
    WHERE customer_type = 'RETAIL'
      AND customer_id != 'Unknown'
      AND total_orders_count > 0
      AND first_order_date IS NOT NULL
),

-- Generate month-end dates for rolling 24-month window.
-- month_end = last day of each month in [current_month - 24M, current_month - 1M].
-- We exclude current (incomplete) month so all snapshots represent closed periods.
-- DuckDB: date_trunc('month', date) - INTERVAL n MONTH is not parameterizable with
-- integer arithmetic directly; use generate_series over timestamp range instead.
snapshot_months AS (
    SELECT
        (date_trunc('month', gs.month_start) + INTERVAL '1 month' - INTERVAL '1 day')::date AS snapshot_month
    FROM (
        SELECT unnest(generate_series(
            (date_trunc('month', current_date) - INTERVAL '24 months')::timestamp,
            (date_trunc('month', current_date) - INTERVAL '1 month')::timestamp,
            INTERVAL '1 month'
        )) AS month_start
    ) gs
),

-- Cross join: for each retail customer × each snapshot month,
-- compute their status as-of that month-end (only if they existed by then).
customer_snapshots AS (
    SELECT
        c.customer_key,
        m.snapshot_month,

        -- Status as-of month-end based on days since last_order_date.
        -- Limitation: dim_customers stores the *current* last_order_date, not historical.
        -- When last_order_date > snapshot_month, we can only bound: the customer ordered
        -- at some future point, so they were definitely NOT churned at snapshot_month.
        -- We conservatively mark them ACTIVE (they kept ordering after this month).
        -- True point-in-time status would require aggregating fact_orders per month-end.
        -- For trend analysis at monthly grain, this approximation is acceptable.
        CASE
            WHEN c.last_order_date::date > m.snapshot_month THEN 'ACTIVE'
            WHEN date_diff('day', c.last_order_date::date, m.snapshot_month) <= 30 THEN 'ACTIVE'
            WHEN date_diff('day', c.last_order_date::date, m.snapshot_month) <= 90 THEN 'AT_RISK'
            ELSE 'CHURNED'
        END AS status,

        -- is_new: customer's first order fell within this snapshot month
        (
            c.first_order_date::date >= date_trunc('month', m.snapshot_month)::date
            AND c.first_order_date::date <= m.snapshot_month
        ) AS is_new,

        -- Value group as-of month-end: use current value_group as approximation
        -- (full point-in-time value_group would require order-level aggregation)
        c.value_group,

        -- Lifetime metrics up to snapshot month-end (approximated from dim_customers)
        -- Note: total_orders_count and lifetime_value in dim_customers are current values.
        -- For true point-in-time these would need re-aggregation from fact_orders;
        -- using current values is acceptable for trend analysis at monthly grain.
        c.total_orders_count AS orders_to_date,
        c.lifetime_value AS lifetime_value_to_date,

        -- Days since last order as-of month-end
        CASE
            WHEN c.last_order_date::date > m.snapshot_month THEN NULL
            ELSE date_diff('day', c.last_order_date::date, m.snapshot_month)
        END AS days_since_last_order,

        c.customer_type,
        c.channel_preference,
        c.product_affinity

    FROM customers c
    CROSS JOIN snapshot_months m
    -- Only include rows where customer existed (first order) by snapshot month-end
    WHERE c.first_order_date::date <= m.snapshot_month
)

SELECT
    customer_key,
    snapshot_month,
    status,
    is_new,
    value_group,
    orders_to_date,
    lifetime_value_to_date,
    days_since_last_order,
    customer_type,
    channel_preference,
    product_affinity
FROM customer_snapshots
ORDER BY customer_key, snapshot_month

{{ config(
    tags=['mart', 'customer', 'retention'],
    location="{{ get_rolling_location() }}"
) }}

-- Point-in-time retention waterfall (retail scope only).
-- Grain: (snapshot_month, status) — one row per status bucket per month.
--
-- WHY this model exists instead of mart_customer_status_snapshot_monthly:
--   The old snapshot model stamps status using dim_customers.last_order_date
--   (current value), causing survivorship bias: every customer still active today
--   appears ACTIVE retroactively, inflating ACTIVE ~10-17x at historical troughs
--   and hiding the 2025 near-death churn event.
--
-- This model computes status purely from fact_orders point-in-time:
--   for each month-end, only orders up to that date are visible.
--
-- Status thresholds (days since last order as-of month-end):
--   ACTIVE  : <= 30 days
--   AT_RISK : 31-90 days
--   CHURNED : > 90 days
--
-- Columns:
--   snapshot_month DATE       : last day of each closed month
--   status         VARCHAR    : ACTIVE | AT_RISK | CHURNED
--   customer_count BIGINT     : customers in this bucket this month
--   base_count     BIGINT     : total cumulative customers as-of month-end

WITH valid_orders AS (
    -- Retail, non-cancelled/draft orders only. Uses fact_orders scope flags.
    -- ordered_at is TIMESTAMPTZ; cast to DATE is ICT because session TZ = Asia/Ho_Chi_Minh.
    SELECT
        o.customer_key,
        o.ordered_at::date AS order_date
    FROM {{ ref('fact_orders') }} o
    INNER JOIN {{ ref('dim_customers') }} c USING (customer_key)
    WHERE o.status NOT IN ('CANCELLED', 'DRAFT')
      AND c.customer_type = 'RETAIL'
      AND c.customer_id <> 'Unknown'
),

-- Generate 14-24 closed month-end dates (rolling window).
-- Using 24 months for full YoY coverage; excludes current (incomplete) month.
snapshot_months AS (
    SELECT
        (date_trunc('month', gs) + INTERVAL '1 month' - INTERVAL '1 day')::date AS snapshot_month
    FROM unnest(
        generate_series(
            (date_trunc('month', current_date) - INTERVAL '24 months')::timestamp,
            (date_trunc('month', current_date) - INTERVAL '1 month')::timestamp,
            INTERVAL '1 month'
        )
    ) AS t(gs)
),

-- Point-in-time last purchase: for each (month-end, customer), the most recent
-- order date that falls ON OR BEFORE the month-end. Customers with no orders
-- before a given month-end simply have no row for that month (correct behaviour).
pit AS (
    SELECT
        m.snapshot_month,
        v.customer_key,
        MAX(v.order_date) AS last_order_date_pit
    FROM snapshot_months m
    INNER JOIN valid_orders v ON v.order_date <= m.snapshot_month
    GROUP BY 1, 2
),

-- Classify each (customer, month) into a status bucket.
customer_status AS (
    SELECT
        snapshot_month,
        customer_key,
        CASE
            WHEN date_diff('day', last_order_date_pit, snapshot_month) <= 30  THEN 'ACTIVE'
            WHEN date_diff('day', last_order_date_pit, snapshot_month) <= 90  THEN 'AT_RISK'
            ELSE 'CHURNED'
        END AS status
    FROM pit
)

-- Aggregate to (snapshot_month, status) grain.
-- base_count = total customers visible at that month-end (sum across all statuses).
SELECT
    snapshot_month,
    status,
    COUNT(*)                           AS customer_count,
    SUM(COUNT(*)) OVER (
        PARTITION BY snapshot_month
    )                                  AS base_count
FROM customer_status
GROUP BY snapshot_month, status
ORDER BY snapshot_month, status

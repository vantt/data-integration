{{ config(
    tags=['mart', 'customer', 'retention'],
    location="{{ get_rolling_location() }}"
) }}

-- Point-in-time retention waterfall (retail scope only).
-- Grain: (snapshot_month, status, value_group, product_affinity, channel_preference).
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
-- Segment dimensions (value_group, product_affinity, channel_preference) use
-- CURRENT attribute values from dim_customers — these are slowly-changing and
-- acceptable for segment-slice analysis. Only the RECENCY-based status is computed
-- point-in-time from fact_orders.
--
-- Columns:
--   snapshot_month      DATE    : last day of each closed month
--   status              VARCHAR : ACTIVE | AT_RISK | CHURNED
--   value_group         VARCHAR : VALUE_VIP | VALUE_GOLD | VALUE_SILVER | VALUE_BRONZE
--   product_affinity    VARCHAR : brand affinity segment from dim_customers
--   channel_preference  VARCHAR : channel preference segment from dim_customers
--   customer_count      BIGINT  : customers in this (status, segment) bucket this month
--   base_count          BIGINT  : total customers visible that month (all statuses + segments)

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

-- Classify each (customer, month) into a status bucket and attach current
-- segment attributes. Segment columns use current dim_customers values —
-- slowly-changing attributes; comment intentional, see model header.
customer_status AS (
    SELECT
        p.snapshot_month,
        p.customer_key,
        CASE
            WHEN date_diff('day', p.last_order_date_pit, p.snapshot_month) <= 30  THEN 'ACTIVE'
            WHEN date_diff('day', p.last_order_date_pit, p.snapshot_month) <= 90  THEN 'AT_RISK'
            ELSE 'CHURNED'
        END AS status,
        c.value_group,
        c.product_affinity,
        c.channel_preference
    FROM pit p
    INNER JOIN {{ ref('dim_customers') }} c USING (customer_key)
)

-- Aggregate to (snapshot_month, status, value_group, product_affinity, channel_preference) grain.
-- base_count = TOTAL customers visible at that month-end across ALL statuses and segments.
-- Each customer appears in exactly one (status, segment) row per month, so
-- SUM(customer_count) OVER (PARTITION BY snapshot_month) still equals the monthly total.
-- To derive segment-level denominators (e.g. all ACTIVE this month), the consuming query
-- must apply a window over the filtered set — base_count is the month-total denominator only.
SELECT
    snapshot_month,
    status,
    value_group,
    product_affinity,
    channel_preference,
    COUNT(*)                           AS customer_count,
    SUM(COUNT(*)) OVER (
        PARTITION BY snapshot_month
    )                                  AS base_count
FROM customer_status
GROUP BY snapshot_month, status, value_group, product_affinity, channel_preference
ORDER BY snapshot_month, status, value_group, product_affinity, channel_preference

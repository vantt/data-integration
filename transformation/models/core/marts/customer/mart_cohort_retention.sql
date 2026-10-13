{{ config(
    tags=['mart', 'customer', 'retention'],
    location="{{ get_rolling_location() }}"
) }}

-- =============================================================================
-- MART: COHORT RETENTION (Multi-Dimensional)
-- =============================================================================
-- Long-format cohort retention table.
-- Grain: 1 row per (cohort_dimension × cohort_value × window_type × period_n).
-- Scope: RETAIL customers only. Min cohort_size = 10 (suppresses thin cohorts).
--
-- 8 single axes + 2 composite axes × 2 window types (relative + calendar).
--
-- window_type='relative'  → period_n = months since first order (0–24)
-- window_type='calendar'  → period_n = 'YYYY-MM' activity month
--
-- Key design notes:
--   - activity CTE computed ONCE, all axes fan out from it (L122)
--   - cohort_size = FIXED denominator (total customers in cohort), not active count
--   - repeat_rate = customers with ≥2 distinct activity_months EVER (cohort-level)
--   - m0_revenue computed from relative period_n=0, broadcast to both window types
-- =============================================================================

WITH

-- ---------------------------------------------------------------------------
-- Entry attributes: one row per retail customer (acquisition-time snapshot)
-- ---------------------------------------------------------------------------
entry AS (
    SELECT * FROM {{ ref('int_customer_entry_attributes') }}
),

-- ---------------------------------------------------------------------------
-- Activity: one row per (customer_key × activity_month) with revenue.
-- Computed ONCE — never re-derived per axis.
-- is_sales_channel=TRUE: excludes internal-arrangement channels (US/Quà Tặng/Other/Unknown/etc.)
-- so zero-value internal orders don't inflate active counts or depress revenue metrics.
-- ---------------------------------------------------------------------------
activity AS (
    SELECT
        o.customer_key,
        DATE_TRUNC('month', o.ordered_at)::DATE  AS activity_month,
        SUM(o.total_collected)                   AS period_revenue
    FROM {{ ref('fact_orders') }} o
    INNER JOIN {{ ref('dim_customers') }} c  ON o.customer_key  = c.customer_key
    INNER JOIN {{ ref('dim_channels') }}  ch ON o.channel_key   = ch.channel_key
                                            AND ch.is_sales_channel = TRUE
    WHERE c.customer_type  = 'RETAIL'
      AND o.is_active_order = TRUE
      AND o.status NOT IN ('CANCELLED', 'DRAFT')
    GROUP BY o.customer_key, DATE_TRUNC('month', o.ordered_at)::DATE
),

-- ---------------------------------------------------------------------------
-- Repeat buyers: customer has ≥2 distinct active months (cohort-level signal)
-- ---------------------------------------------------------------------------
customer_is_repeat AS (
    SELECT
        customer_key,
        CASE WHEN COUNT(DISTINCT activity_month) >= 2 THEN 1 ELSE 0 END AS is_repeat
    FROM activity
    GROUP BY customer_key
),

-- ---------------------------------------------------------------------------
-- Axis CTEs: map each customer to a cohort_value for each dimension.
-- Each CTE produces: (customer_key, cohort_dimension, cohort_value)
-- ---------------------------------------------------------------------------
axis_first_order_month AS (
    SELECT
        customer_key,
        'first_order_month'                              AS cohort_dimension,
        STRFTIME('%Y-%m', first_order_month)               AS cohort_value,
        first_order_month
    FROM entry
),

axis_entry_product AS (
    SELECT
        customer_key,
        'entry_product'                                  AS cohort_dimension,
        COALESCE(entry_product_name, 'Unknown')          AS cohort_value,
        first_order_month
    FROM entry
),

axis_entry_category AS (
    SELECT
        customer_key,
        'entry_category'                                 AS cohort_dimension,
        COALESCE(entry_category, 'Khác')                 AS cohort_value,
        first_order_month
    FROM entry
),

axis_acquisition_channel AS (
    SELECT
        customer_key,
        'acquisition_channel'                            AS cohort_dimension,
        COALESCE(acquisition_channel_name, 'Unknown')    AS cohort_value,
        first_order_month
    FROM entry
),

axis_basket_size AS (
    SELECT
        customer_key,
        'basket_size'                                    AS cohort_dimension,
        basket_size                                      AS cohort_value,
        first_order_month
    FROM entry
),

axis_entry_value_band AS (
    SELECT
        customer_key,
        'entry_value_band'                               AS cohort_dimension,
        entry_value_band                                 AS cohort_value,
        first_order_month
    FROM entry
),

axis_product_x_channel AS (
    SELECT
        customer_key,
        'entry_product × acquisition_channel'            AS cohort_dimension,
        CONCAT(
            COALESCE(entry_product_name, 'Unknown'),
            ' × ',
            COALESCE(acquisition_channel_name, 'Unknown')
        )                                                AS cohort_value,
        first_order_month
    FROM entry
),

axis_basket_x_value AS (
    SELECT
        customer_key,
        'basket_size × entry_value_band'                 AS cohort_dimension,
        CONCAT(basket_size, ' × ', entry_value_band)     AS cohort_value,
        first_order_month
    FROM entry
),

-- ---------------------------------------------------------------------------
-- Union all axis rows: (customer_key, cohort_dimension, cohort_value, first_order_month)
-- ---------------------------------------------------------------------------
customer_axis AS (
    SELECT * FROM axis_first_order_month
    UNION ALL
    SELECT * FROM axis_entry_product
    UNION ALL
    SELECT * FROM axis_entry_category
    UNION ALL
    SELECT * FROM axis_acquisition_channel
    UNION ALL
    SELECT * FROM axis_basket_size
    UNION ALL
    SELECT * FROM axis_entry_value_band
    UNION ALL
    SELECT * FROM axis_product_x_channel
    UNION ALL
    SELECT * FROM axis_basket_x_value
),

-- ---------------------------------------------------------------------------
-- Cohort sizes: fixed denominator — total customers per (dimension, value)
-- ---------------------------------------------------------------------------
cohort_sizes AS (
    SELECT
        cohort_dimension,
        cohort_value,
        COUNT(DISTINCT customer_key) AS cohort_size
    FROM customer_axis
    GROUP BY cohort_dimension, cohort_value
),

-- ---------------------------------------------------------------------------
-- Repeat customers per cohort: broadcast cohort-level repeat signal
-- ---------------------------------------------------------------------------
repeat_per_cohort AS (
    SELECT
        ca.cohort_dimension,
        ca.cohort_value,
        SUM(COALESCE(cir.is_repeat, 0)) AS repeat_customers
    FROM customer_axis ca
    LEFT JOIN customer_is_repeat cir ON ca.customer_key = cir.customer_key
    GROUP BY ca.cohort_dimension, ca.cohort_value
),

-- ---------------------------------------------------------------------------
-- Activity joined to axes: cross (cohort_dimension, cohort_value) × activity
-- Only include activity_month >= customer's first_order_month
-- ---------------------------------------------------------------------------
activity_joined AS (
    SELECT
        ca.cohort_dimension,
        ca.cohort_value,
        ca.customer_key,
        ca.first_order_month,
        a.activity_month,
        a.period_revenue,
        CAST(DATEDIFF('month', ca.first_order_month, a.activity_month) AS INTEGER) AS period_n_int
    FROM customer_axis ca
    INNER JOIN activity a ON ca.customer_key = a.customer_key
    WHERE a.activity_month >= ca.first_order_month
),

-- ---------------------------------------------------------------------------
-- Relative window aggregates: period_n 0–24
-- ---------------------------------------------------------------------------
relative_agg AS (
    SELECT
        cohort_dimension,
        cohort_value,
        period_n_int,
        COUNT(DISTINCT customer_key)   AS active,
        SUM(period_revenue)            AS revenue
    FROM activity_joined
    WHERE period_n_int BETWEEN 0 AND 24
    GROUP BY cohort_dimension, cohort_value, period_n_int
),

-- ---------------------------------------------------------------------------
-- M0 revenue per cohort: used as revenue denominator for both window types
-- ---------------------------------------------------------------------------
m0_revenue_per_cohort AS (
    SELECT
        cohort_dimension,
        cohort_value,
        revenue AS m0_revenue
    FROM relative_agg
    WHERE period_n_int = 0
),

-- ---------------------------------------------------------------------------
-- Calendar window aggregates: period_n = 'YYYY-MM'
-- ---------------------------------------------------------------------------
calendar_agg AS (
    SELECT
        cohort_dimension,
        cohort_value,
        STRFTIME('%Y-%m', activity_month)  AS period_n,
        COUNT(DISTINCT customer_key)     AS active,
        SUM(period_revenue)              AS revenue
    FROM activity_joined
    GROUP BY cohort_dimension, cohort_value, STRFTIME('%Y-%m', activity_month)
),

-- ---------------------------------------------------------------------------
-- Final relative rows
-- ---------------------------------------------------------------------------
final_relative AS (
    SELECT
        ra.cohort_dimension,
        ra.cohort_value,
        'relative'                                                  AS window_type,
        CAST(ra.period_n_int AS VARCHAR)                            AS period_n,
        cs.cohort_size,
        ra.active,
        ra.active * 100.0 / NULLIF(cs.cohort_size, 0)              AS retention_pct,
        ra.revenue,
        m0.m0_revenue,
        ra.revenue / NULLIF(m0.m0_revenue, 0)                      AS revenue_retention,
        rpc.repeat_customers,
        rpc.repeat_customers * 100.0 / NULLIF(cs.cohort_size, 0)   AS repeat_rate
    FROM relative_agg ra
    INNER JOIN cohort_sizes cs         ON ra.cohort_dimension = cs.cohort_dimension
                                      AND ra.cohort_value     = cs.cohort_value
    LEFT JOIN  m0_revenue_per_cohort m0 ON ra.cohort_dimension = m0.cohort_dimension
                                       AND ra.cohort_value     = m0.cohort_value
    LEFT JOIN  repeat_per_cohort rpc   ON ra.cohort_dimension = rpc.cohort_dimension
                                      AND ra.cohort_value     = rpc.cohort_value
),

-- ---------------------------------------------------------------------------
-- Final calendar rows
-- ---------------------------------------------------------------------------
final_calendar AS (
    SELECT
        ca.cohort_dimension,
        ca.cohort_value,
        'calendar'                                                  AS window_type,
        ca.period_n,
        cs.cohort_size,
        ca.active,
        ca.active * 100.0 / NULLIF(cs.cohort_size, 0)              AS retention_pct,
        ca.revenue,
        m0.m0_revenue,
        ca.revenue / NULLIF(m0.m0_revenue, 0)                      AS revenue_retention,
        rpc.repeat_customers,
        rpc.repeat_customers * 100.0 / NULLIF(cs.cohort_size, 0)   AS repeat_rate
    FROM calendar_agg ca
    INNER JOIN cohort_sizes cs          ON ca.cohort_dimension = cs.cohort_dimension
                                       AND ca.cohort_value     = cs.cohort_value
    LEFT JOIN  m0_revenue_per_cohort m0 ON ca.cohort_dimension = m0.cohort_dimension
                                       AND ca.cohort_value     = m0.cohort_value
    LEFT JOIN  repeat_per_cohort rpc    ON ca.cohort_dimension = rpc.cohort_dimension
                                       AND ca.cohort_value     = rpc.cohort_value
)

-- ---------------------------------------------------------------------------
-- Union relative + calendar; suppress thin cohorts (cohort_size < 10)
-- ---------------------------------------------------------------------------
SELECT
    cohort_dimension,
    cohort_value,
    window_type,
    period_n,
    cohort_size::INTEGER        AS cohort_size,
    active::INTEGER             AS active,
    retention_pct::DOUBLE       AS retention_pct,
    revenue::BIGINT             AS revenue,
    m0_revenue::BIGINT          AS m0_revenue,
    revenue_retention::DOUBLE   AS revenue_retention,
    repeat_customers::INTEGER   AS repeat_customers,
    repeat_rate::DOUBLE         AS repeat_rate
FROM final_relative
WHERE cohort_size >= 10

UNION ALL

SELECT
    cohort_dimension,
    cohort_value,
    window_type,
    period_n,
    cohort_size::INTEGER        AS cohort_size,
    active::INTEGER             AS active,
    retention_pct::DOUBLE       AS retention_pct,
    revenue::BIGINT             AS revenue,
    m0_revenue::BIGINT          AS m0_revenue,
    revenue_retention::DOUBLE   AS revenue_retention,
    repeat_customers::INTEGER   AS repeat_customers,
    repeat_rate::DOUBLE         AS repeat_rate
FROM final_calendar
WHERE cohort_size >= 10

# 📘 Blueprint: Customer Retention & Lifecycle

> **Target Collection:** `Marketing & Customers`
> **Design Spec:** `designs/customer_retention_lifecycle.md`
> **Role:** Marketing Manager, Customer Success, CEO
> **Archetype:** Operational Cockpit (3 tabs)

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Customer Retention & Lifecycle

**Description**: Strategic retention analytics — repeat purchase rates, churn trends, cohort retention heatmap, revenue layer cake, purchase frequency distribution, reactivation tracking, and at-risk watchlist. 3 tabs: Suc khoe Retention, Phan tich Cohort, Hanh vi & Reactivation.

---

#### Filter: Segment

```json metabase-filter
{
  "slug": "segment",
  "type": "string/="
}
```

---

### 📑 Tab: Suc khoe Retention

#### 📝 Text: Monitor retention health — repeat rate, churn, and lifecycle status

# Monitor retention health — repeat rate, churn, and lifecycle status

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Assess lifecycle distribution — where are customers concentrating?

# Assess lifecycle distribution — where are customers concentrating?

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Track retention and churn trends — are we improving toward target?

# Track retention and churn trends — are we improving toward target?

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Review retention scorecard — flag segments with weak retention

# Review retention scorecard — flag segments with weak retention

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Repeat Purchase Rate

Hero metric — percentage of customers who have made more than one purchase, with MoM comparison.

```sql
WITH current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN total_orders_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN total_orders_count > 1
                       AND last_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
                  THEN 1 END) * 100.0
            / NULLIF(COUNT(CASE WHEN first_order_date < date_trunc('month', current_date) - INTERVAL '1 month' THEN 1 END), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
)
SELECT
    c.value as "Repeat Rate %",
    p.value as "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ],
    "column_settings": { "Repeat Rate %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Churn Rate

Percentage of customers churned (90+ days inactive), with MoM comparison. Lower is better.

```sql
WITH current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) * 100.0
            / NULLIF(COUNT(*), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN recency_days + 30 > 90 THEN 1 END) * 100.0
            / NULLIF(COUNT(CASE WHEN first_order_date < date_trunc('month', current_date) - INTERVAL '1 month' THEN 1 END), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
)
SELECT
    c.value as "Churn Rate %",
    p.value as "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ],
    "column_settings": { "Churn Rate %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Customer Lifespan

Average days between first and last order for repeat customers, with MoM comparison.

```sql
WITH current_period AS (
    SELECT ROUND(AVG(lifespan_days), 0) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 1
      AND lifespan_days > 0
      [[AND value_group = {{segment}}]]
),
previous_period AS (
    SELECT ROUND(AVG(lifespan_days), 0) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 1
      AND lifespan_days > 0
      AND last_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND value_group = {{segment}}]]
)
SELECT
    c.value as "Avg Lifespan (days)",
    p.value as "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ],
    "column_settings": { "Avg Lifespan (days)": { "suffix": " days" } }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Active Customer Rate

Percentage of paying customers active in last 30 days, with MoM comparison.

```sql
WITH current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0
            / NULLIF(COUNT(*), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN recency_days BETWEEN 31 AND 60 THEN 1 END) * 100.0
            / NULLIF(COUNT(CASE WHEN first_order_date < date_trunc('month', current_date) - INTERVAL '1 month' THEN 1 END), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
)
SELECT
    c.value as "Active Rate %",
    p.value as "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ],
    "column_settings": { "Active Rate %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Customer Lifecycle Distribution

Donut chart showing Active / At Risk / Churned distribution.

```sql
SELECT
    customer_status as "Status",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
  AND customer_status IN ('Active', 'At Risk', 'Churned')
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY
    CASE customer_status
        WHEN 'Active' THEN 1
        WHEN 'At Risk' THEN 2
        WHEN 'Churned' THEN 3
    END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": ["Status"],
    "pie.metric": "Customers",
    "pie.colors": {
      "Active": "#509EE3",
      "At Risk": "#F9D45C",
      "Churned": "#EF8C8C"
    },
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 30 ngày gần nhất: ' ||
  strftime(current_date - 29, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  So sánh: ' ||
  strftime(current_date - 59, '%d/%m/%Y') || ' – ' || strftime(current_date - 30, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### ❓ Question: Revenue by Lifecycle Status

Total lifetime value concentrated in each lifecycle status.

```sql
SELECT
    customer_status as "Status",
    SUM(lifetime_value) as "Total LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
  AND customer_status IN ('Active', 'At Risk', 'Churned')
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY
    CASE customer_status
        WHEN 'Active' THEN 1
        WHEN 'At Risk' THEN 2
        WHEN 'Churned' THEN 3
    END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Status"],
    "graph.metrics": ["Total LTV"],
    "graph.colors": ["#509EE3", "#F9D45C", "#EF8C8C"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Lifetime Value (VND)",
    "column_settings": {
      "Total LTV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 7, "col":6, "size_x":6, "size_y":6}
```

#### ❓ Question: Segment x Status Matrix

Stacked bar showing lifecycle status distribution within each customer segment.

```sql
SELECT
    value_group as "Segment",
    customer_status as "Status",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
  AND customer_status IN ('Active', 'At Risk', 'Churned')
  [[AND value_group = {{segment}}]]
GROUP BY 1, 2
ORDER BY
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 ELSE 3 END,
    CASE customer_status WHEN 'Active' THEN 1 WHEN 'At Risk' THEN 2 ELSE 3 END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Segment"],
    "graph.metrics": ["Customers"],
    "graph.group_by": ["Status"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#509EE3", "#F9D45C", "#EF8C8C"]
  }
}
```

```json metabase-pos
{"row": 7, "col":12, "size_x":6, "size_y":6}
```

---

#### ❓ Question: Churn Rate Trend (6M)

Monthly churn rate with goal line — target below 40%.

```sql
SELECT
    date_trunc('month', last_order_date + INTERVAL '90' DAY)::date as month,
    COUNT(customer_id) as churned_customers,
    ROUND(
        COUNT(customer_id) * 100.0 / NULLIF(
            (SELECT COUNT(*) FROM dim_customers WHERE total_orders_count > 0 AND customer_id != 'Unknown'), 0
        ), 1
    ) as "Churn Rate %"
FROM dim_customers
WHERE customer_status = 'Churned'
  AND (last_order_date + INTERVAL '90' DAY) >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND (last_order_date + INTERVAL '90' DAY) < date_trunc('month', current_date)
  AND customer_id != 'Unknown'
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Churn Rate %"],
    "graph.colors": ["#EF8C8C"],
    "graph.goal_value": 40,
    "graph.show_goal": true,
    "graph.goal_label": "Target < 40%",
    "graph.y_axis.title_text": "Churn Rate %"
  }
}
```

```json metabase-pos
{"row": 14, "col":0, "size_x":9, "size_y":6}
```

#### ❓ Question: Repeat Purchase Rate Trend (6M)

Monthly trend of repeat purchase rate among buyers each month.

```sql
WITH monthly_buyers AS (
    SELECT
        date_trunc('month', order_timestamp)::date as month,
        customer_key,
        COUNT(DISTINCT order_id) as orders_in_month
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND order_timestamp < date_trunc('month', current_date)
    GROUP BY 1, 2
)
SELECT
    month,
    COUNT(*) as "Total Buyers",
    COUNT(CASE WHEN orders_in_month > 1 THEN 1 END) as "Repeat Buyers",
    ROUND(
        COUNT(CASE WHEN orders_in_month > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
    ) as "Repeat %"
FROM monthly_buyers
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Repeat %"],
    "graph.colors": ["#84BB4C"],
    "graph.y_axis.title_text": "Repeat %"
  }
}
```

```json metabase-pos
{"row": 14, "col":9, "size_x":9, "size_y":6}
```

---

#### ❓ Question: Retention Health Scorecard

Per-segment retention vitals with conditional formatting.

```sql
SELECT
    value_group as "Segment",
    COUNT(*) as "Customers",
    ROUND(COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Active %",
    ROUND(COUNT(CASE WHEN customer_status = 'At Risk' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "At Risk %",
    ROUND(COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Churned %",
    ROUND(COUNT(CASE WHEN total_orders_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Repeat Rate %",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV",
    ROUND(AVG(recency_days), 0) as "Avg Recency (days)"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 ELSE 3 END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Active %"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      },
      {
        "columns": ["Churned %"],
        "type": "range",
        "colors": ["#84BB4C", "#F9D45C", "#EF8C8C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      }
    ],
    "column_settings": {
      "Avg LTV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Active %": { "suffix": "%" },
      "At Risk %": { "suffix": "%" },
      "Churned %": { "suffix": "%" },
      "Repeat Rate %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{"row": 21, "col":0, "size_x":18, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** monthly-cohort · **Scope:** customer_type='RETAIL' · **Caveats:** Cohort rolling
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Phan tich Cohort


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Cohort tháng: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Analyze cohort retention — which cohorts stick, which churn early?

# Analyze cohort retention — which cohorts stick, which churn early?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Examine cohort retention matrix — identify drop-off patterns

# Examine cohort retention matrix — identify drop-off patterns

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Track revenue by cohort — are recent cohorts contributing enough?

# Track revenue by cohort — are recent cohorts contributing enough?

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Compare new vs returning — revenue dependency and growth quality

# Compare new vs returning — revenue dependency and growth quality

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Avg Month-1 Retention

Average M1 retention rate across recent cohorts — early lifecycle health indicator.

```sql
WITH cohort_sizes AS (
    SELECT
        date_trunc('month', first_order_date) as cohort_month,
        COUNT(DISTINCT customer_id) as original_size
    FROM dim_customers
    WHERE first_order_date >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND customer_id != 'Unknown'
    GROUP BY 1
),
m1_retention AS (
    SELECT
        date_trunc('month', c.first_order_date) as cohort_month,
        COUNT(DISTINCT c.customer_id) as retained
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
    WHERE c.first_order_date >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND c.first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND c.customer_id != 'Unknown'
      AND date_diff('month', c.first_order_date, o.order_timestamp) = 1
      AND o.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1
)
SELECT
    ROUND(AVG(CAST(r.retained AS FLOAT) / s.original_size * 100), 1) as "Avg M1 Retention %"
FROM cohort_sizes s
LEFT JOIN m1_retention r ON s.cohort_month = r.cohort_month
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Avg M1 Retention %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Best Cohort (M1 Retention)

Which acquisition month had the highest Month-1 retention rate.

```sql
WITH cohort_sizes AS (
    SELECT
        date_trunc('month', first_order_date) as cohort_month,
        COUNT(DISTINCT customer_id) as original_size
    FROM dim_customers
    WHERE first_order_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND customer_id != 'Unknown'
    GROUP BY 1
),
m1_retention AS (
    SELECT
        date_trunc('month', c.first_order_date) as cohort_month,
        COUNT(DISTINCT c.customer_id) as retained
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
    WHERE c.first_order_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND c.first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
      AND c.customer_id != 'Unknown'
      AND date_diff('month', c.first_order_date, o.order_timestamp) = 1
      AND o.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1
)
SELECT
    strftime(s.cohort_month, '%Y-%m') as "Best Cohort",
    ROUND(CAST(r.retained AS FLOAT) / s.original_size * 100, 1) as "M1 %"
FROM cohort_sizes s
LEFT JOIN m1_retention r ON s.cohort_month = r.cohort_month
ORDER BY 2 DESC
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "M1 %": { "suffix": "%" } }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Orders per Customer

Average number of orders among paying customers, with MoM comparison.

```sql
WITH current_period AS (
    SELECT ROUND(AVG(total_orders_count), 1) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
),
previous_period AS (
    SELECT ROUND(AVG(total_orders_count), 1) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      AND first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    c.value as "Avg Orders",
    p.value as "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Returning Revenue Ratio

Percentage of total revenue coming from returning customers.

```sql
SELECT
    ROUND(
        SUM(CASE
            WHEN date_trunc('month', o.order_timestamp) != date_trunc('month', c.first_order_date)
            THEN o.net_revenue ELSE 0
        END) * 100.0 / NULLIF(SUM(o.net_revenue), 0), 1
    ) as "Returning Revenue %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Returning Revenue %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Cohort Retention Heatmap

Percentage of customers returning in subsequent months after first purchase (12-month lookback).

```sql
WITH cohort_sizes AS (
    SELECT
        date_trunc('month', first_order_date) as cohort_month,
        COUNT(DISTINCT customer_id) as original_size
    FROM dim_customers
    WHERE first_order_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND customer_id != 'Unknown'
    GROUP BY 1
),
retention_activity AS (
    SELECT
        date_trunc('month', c.first_order_date) as cohort_month,
        date_diff('month', c.first_order_date, o.order_timestamp) as month_number,
        COUNT(DISTINCT c.customer_id) as active_customers
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
    WHERE c.first_order_date >= date_trunc('month', current_date) - INTERVAL '12 months'
      AND o.order_timestamp >= c.first_order_date
      AND c.customer_id != 'Unknown'
      AND o.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1, 2
)
SELECT
    strftime(r.cohort_month, '%Y-%m') as "Cohort",
    r.month_number as "Month #",
    s.original_size as "Cohort Size",
    r.active_customers as "Active",
    ROUND(CAST(r.active_customers AS FLOAT) / s.original_size * 100, 1) as "Retention %"
FROM retention_activity r
JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
WHERE r.month_number BETWEEN 0 AND 12
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "pivot",
  "visualization_settings": {
    "pivot_table.column_split": {
      "rows": ["Cohort"],
      "columns": ["Month #"],
      "values": ["Retention %"]
    },
    "table.column_formatting": [
      {
        "columns": ["Retention %"],
        "type": "range",
        "colors": ["#EF8C8C", "#F9D45C", "#84BB4C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 9 }
```

---

#### ❓ Question: Revenue by Cohort (Layer Cake)

Total revenue by acquisition cohort over time — shows legacy vs new contribution.

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as revenue_month,
    strftime(date_trunc('month', c.first_order_date), '%Y-%m') as cohort,
    SUM(o.net_revenue) as revenue
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '12 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["revenue_month"],
    "graph.metrics": ["revenue"],
    "graph.group_by": ["cohort"],
    "stackable.stack_type": "stacked",
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: New vs Returning Revenue (6M)

Monthly revenue split by new customers (first order month) vs returning customers.

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as month,
    CASE
        WHEN date_trunc('month', o.order_timestamp) = date_trunc('month', c.first_order_date)
        THEN 'New Customer'
        ELSE 'Returning Customer'
    END as customer_type,
    SUM(o.net_revenue) as revenue
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["revenue"],
    "graph.group_by": ["customer_type"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#509EE3", "#84BB4C"],
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 22, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New vs Returning Customers (6M)

Monthly count of new vs returning purchasers.

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as month,
    CASE
        WHEN date_trunc('month', o.order_timestamp) = date_trunc('month', c.first_order_date)
        THEN 'New Customer'
        ELSE 'Returning Customer'
    END as customer_type,
    COUNT(DISTINCT c.customer_id) as customers
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND c.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["customers"],
    "graph.group_by": ["customer_type"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#509EE3", "#84BB4C"],
    "graph.y_axis.title_text": "Customers"
  }
}
```

```json metabase-pos
{ "row": 22, "col": 9, "size_x": 9, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** monthly-cohort · **Scope:** customer_type='RETAIL' · **Caveats:** Cohort rolling
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Hanh vi & Reactivation


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Cohort tháng: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Analyze purchase behavior — timing signals and reactivation effectiveness

# Analyze purchase behavior — timing signals and reactivation effectiveness

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Examine purchase frequency — distribution shape and conversion opportunity

# Examine purchase frequency — distribution shape and conversion opportunity

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Track reactivation performance — is win-back ROI improving?

# Track reactivation performance — is win-back ROI improving?

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Prioritize at-risk outreach — high-value customers needing action NOW

# Prioritize at-risk outreach — high-value customers needing action NOW

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Avg Days Between Purchases

Hero metric — average inter-purchase gap for repeat customers, with MoM comparison.

```sql
WITH purchase_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.order_timestamp) OVER (PARTITION BY o.customer_key ORDER BY o.order_timestamp) AS DATE),
            CAST(o.order_timestamp AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
),
current_val AS (
    SELECT ROUND(AVG(days_between), 0) as value
    FROM purchase_gaps
    WHERE days_between > 0
),
prev_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.order_timestamp) OVER (PARTITION BY o.customer_key ORDER BY o.order_timestamp) AS DATE),
            CAST(o.order_timestamp AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.customer_id != 'Unknown'
      AND o.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND c.value_group = {{segment}}]]
),
prev_val AS (
    SELECT ROUND(AVG(days_between), 0) as value
    FROM prev_gaps
    WHERE days_between > 0
)
SELECT
    c.value as "Avg Gap (days)",
    p.value as "Prev Month"
FROM current_val c, prev_val p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ],
    "column_settings": { "Avg Gap (days)": { "suffix": " days" } }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Reactivated Customers (Last Month)

Customers who returned after 30+ days gap, with MoM comparison.

```sql
WITH reactivated_current AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT customer_key, MAX(order_timestamp) as prev_order
        FROM fact_orders
        WHERE status NOT IN ('CANCELLED', 'Voided')
          AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
        GROUP BY 1
    ) prev ON o.customer_key = prev.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.order_timestamp < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      AND date_diff('day', CAST(prev.prev_order AS DATE), CAST(o.order_timestamp AS DATE)) > 30
      [[AND c.value_group = {{segment}}]]
),
reactivated_prev AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT customer_key, MAX(order_timestamp) as prev_order
        FROM fact_orders
        WHERE status NOT IN ('CANCELLED', 'Voided')
          AND order_timestamp < date_trunc('month', current_date) - INTERVAL '2 months'
        GROUP BY 1
    ) prev ON o.customer_key = prev.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      AND c.customer_id != 'Unknown'
      AND date_diff('day', CAST(prev.prev_order AS DATE), CAST(o.order_timestamp AS DATE)) > 30
      [[AND c.value_group = {{segment}}]]
)
SELECT
    c.value as "Reactivated",
    p.value as "Prev Month"
FROM reactivated_current c, reactivated_prev p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: At-Risk Customers Count

Count of customers in At Risk status (31-90 days since last purchase).

```sql
SELECT
    COUNT(*) as "At Risk"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND customer_status = 'At Risk'
  AND total_orders_count > 0
  [[AND value_group = {{segment}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: One-Time Buyer Rate

Percentage of customers with exactly 1 order — conversion opportunity. Lower is better.

```sql
WITH current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN total_orders_count = 1 THEN 1 END) * 100.0
            / NULLIF(COUNT(*), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN total_orders_count = 1
                       AND first_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
                  THEN 1 END) * 100.0
            / NULLIF(COUNT(CASE WHEN first_order_date < date_trunc('month', current_date) - INTERVAL '1 month' THEN 1 END), 0), 1
        ) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND total_orders_count > 0
      [[AND value_group = {{segment}}]]
)
SELECT
    c.value as "One-Time %",
    p.value as "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Prev Month",
        "label": "vs prev month"
      }
    ],
    "column_settings": { "One-Time %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Purchase Frequency Distribution

How many orders do customers typically place? Understand one-time vs repeat behavior.

```sql
SELECT
    CASE
        WHEN total_orders_count = 1 THEN '1 order'
        WHEN total_orders_count = 2 THEN '2 orders'
        WHEN total_orders_count = 3 THEN '3 orders'
        WHEN total_orders_count BETWEEN 4 AND 5 THEN '4-5 orders'
        WHEN total_orders_count BETWEEN 6 AND 10 THEN '6-10 orders'
        ELSE '11+ orders'
    END as "Order Count",
    COUNT(*) as "Customers",
    ROUND(
        COUNT(*) * 100.0 / NULLIF(
            (SELECT COUNT(*) FROM dim_customers WHERE total_orders_count > 0 AND customer_id != 'Unknown'), 0
        ), 1
    ) as "% of Total"
FROM dim_customers
WHERE total_orders_count > 0
  AND customer_id != 'Unknown'
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY MIN(total_orders_count)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Order Count"],
    "graph.metrics": ["Customers"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Order Frequency",
    "graph.y_axis.title_text": "Customers"
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Days Between Purchases Distribution

For repeat customers, how long between purchases? Helps set reactivation timing.

```sql
WITH purchase_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.order_timestamp) OVER (PARTITION BY o.customer_key ORDER BY o.order_timestamp) AS DATE),
            CAST(o.order_timestamp AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
)
SELECT
    CASE
        WHEN days_between <= 7 THEN '0-7 days'
        WHEN days_between <= 14 THEN '8-14 days'
        WHEN days_between <= 30 THEN '15-30 days'
        WHEN days_between <= 60 THEN '31-60 days'
        WHEN days_between <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END as "Gap",
    COUNT(*) as "Occurrences",
    ROUND(
        COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0), 1
    ) as "% of Total"
FROM purchase_gaps
WHERE days_between IS NOT NULL
  AND days_between > 0
GROUP BY 1
ORDER BY MIN(days_between)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Gap"],
    "graph.metrics": ["Occurrences"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "Days Between Purchases",
    "graph.y_axis.title_text": "Occurrences"
  }
}
```

```json metabase-pos
{ "row": 5, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Reactivation Trend (6M)

Monthly count of reactivated customers (returned after 30+ day gap) with revenue contribution.

```sql
WITH reactivated AS (
    SELECT
        date_trunc('month', o.order_timestamp)::date as month,
        o.customer_key,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT
            customer_key,
            order_timestamp,
            LAG(order_timestamp) OVER (PARTITION BY customer_key ORDER BY order_timestamp) as prev_order
        FROM fact_orders
        WHERE status NOT IN ('CANCELLED', 'Voided')
    ) gaps ON o.customer_key = gaps.customer_key
        AND o.order_timestamp = gaps.order_timestamp
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND gaps.prev_order IS NOT NULL
      AND date_diff('day', CAST(gaps.prev_order AS DATE), CAST(o.order_timestamp AS DATE)) > 30
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND o.order_timestamp < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
    GROUP BY 1, 2
)
SELECT
    month,
    COUNT(DISTINCT customer_key) as "Reactivated Customers",
    SUM(revenue) as "Reactivation Revenue"
FROM reactivated
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Reactivated Customers", "Reactivation Revenue"],
    "series_settings": {
      "Reactivated Customers": { "display": "bar", "color": "#84BB4C" },
      "Reactivation Revenue": { "display": "line", "color": "#7172AD" }
    },
    "graph.y_axis.title_text": "Customers",
    "column_settings": {
      "Reactivation Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: At-Risk Customer Watchlist

High-value At Risk customers needing outreach — sorted by LTV descending.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    value_group as "Segment",
    last_order_date as "Last Order",
    recency_days as "Days Since",
    lifetime_value as "Lifetime Value",
    total_orders_count as "Orders"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND customer_status = 'At Risk'
  AND total_orders_count > 0
  [[AND value_group = {{segment}}]]
ORDER BY lifetime_value DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Lifetime Value"],
        "type": "range",
        "colors": ["#FFFFFF", "#7172AD"],
        "min_type": "min",
        "max_type": "max"
      },
      {
        "columns": ["Days Since"],
        "type": "range",
        "colors": ["#F9D45C", "#EF8C8C"],
        "min_type": "custom",
        "min_value": 31,
        "max_type": "custom",
        "max_value": 90
      }
    ],
    "column_settings": {
      "Lifetime Value": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Footer

Source: dim_customers · fact_orders · Updated monthly · Excludes Unknown & cancelled orders

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** monthly-cohort · **Scope:** customer_type='RETAIL' · **Caveats:** Cohort rolling
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


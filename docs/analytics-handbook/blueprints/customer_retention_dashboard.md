---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts:
  - scope_retail
  - is_active_order
---

# 📘 Blueprint: Customer Retention & Lifecycle [Retail]

> **Target Collection:** `Marketing & Customers`
> **Design Spec:** `designs/customer_retention_lifecycle.md`
> **Role:** Marketing Manager, Customer Success, CEO
> **Archetype:** Operational Cockpit (3 tabs)

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail)
## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Customer Retention & Lifecycle [Retail]

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
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Assess lifecycle distribution — where are customers concentrating?

# Assess lifecycle distribution — where are customers concentrating?

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Track retention and churn trends — are we improving toward target?

# Track retention and churn trends — are we improving toward target?

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Review retention scorecard — flag segments with weak retention

# Review retention scorecard — flag segments with weak retention

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Repeat Purchase Rate

Hero metric — percentage of customers who have made more than one purchase, with MoM comparison.

```sql
-- Snapshot-driven MoM: compares state at end of this month vs end of last month.
-- current_month_end = last day of previous calendar month (most recent closed month)
-- prev_month_end    = last day of the month before that
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN orders_to_date > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      [[AND s.value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN orders_to_date > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      [[AND s.value_group = {{segment}}]]
)
SELECT
    c.value AS "Repeat Rate %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Repeat Rate %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Churn Rate

Percentage of customers churned (90+ days inactive), with MoM comparison. Lower is better.

```sql
-- Snapshot-driven MoM: status = 'CHURNED' as-of each month-end snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN status = 'CHURNED' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      [[AND s.value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN status = 'CHURNED' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      [[AND s.value_group = {{segment}}]]
)
SELECT
    c.value AS "Churn Rate %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Churn Rate %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Order Value

Average revenue per order for repeat customers (LTV ÷ orders), with MoM comparison.

```sql
-- Snapshot-driven MoM: avg days_since_last_order for customers active (not churned)
-- as-of each month-end. Proxy for lifespan using snapshot recency.
-- For repeat customers only (orders_to_date > 1).
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT ROUND(AVG(lifetime_value_to_date / NULLIF(orders_to_date, 0)), 0) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      AND s.orders_to_date > 1
      [[AND s.value_group = {{segment}}]]
),
previous_period AS (
    SELECT ROUND(AVG(lifetime_value_to_date / NULLIF(orders_to_date, 0)), 0) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      AND s.orders_to_date > 1
      [[AND s.value_group = {{segment}}]]
)
SELECT
    c.value AS "Avg Order Value",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg Order Value": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Active Customer Rate

Percentage of paying customers active in last 30 days, with MoM comparison.

```sql
-- Snapshot-driven MoM: status = 'ACTIVE' as-of each month-end snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      [[AND s.value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      [[AND s.value_group = {{segment}}]]
)
SELECT
    c.value AS "Active Rate %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Active Rate %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 14, "size_x": 4, "size_y": 3 }
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
  AND order_count > 0
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
{ "row": 7, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Tháng hiện tại: ' ||
  strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  So sánh: tháng ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%m/%Y')
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
  AND order_count > 0
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
{"row": 8, "col":6, "size_x":6, "size_y":6}
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
  AND order_count > 0
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
{"row": 8, "col":12, "size_x":6, "size_y":6}
```

---

#### ❓ Question: Retention Waterfall Trend (6M)

Point-in-time lifecycle status counts per month — ACTIVE / AT_RISK / CHURNED from survivorship-free waterfall model.

```sql
-- Point-in-time trend from mart_retention_waterfall_monthly (grain: snapshot_month x status).
-- Replaces survivorship-biased mart_customer_status_snapshot_monthly for this trend view.
SELECT
    snapshot_month AS month,
    status AS "Status",
    customer_count AS "Customers"
FROM mart_retention_waterfall_monthly
WHERE snapshot_month >= (date_trunc('month', current_date) - INTERVAL '6 months')::date
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Customers"],
    "graph.group_by": ["Status"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#509EE3", "#F9D45C", "#EF8C8C"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Customers"
  }
}
```

```json metabase-pos
{"row": 15, "col":0, "size_x":9, "size_y":6}
```

#### ❓ Question: Repeat Purchase Rate Trend (6M)

Monthly trend of repeat purchase rate among buyers each month.

```sql
WITH monthly_buyers AS (
    SELECT
        date_trunc('month', o.ordered_at)::date as month,
        o.customer_key,
        COUNT(DISTINCT o.order_id) as orders_in_month
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND o.ordered_at < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      [[AND c.value_group = {{segment}}]]
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
{"row": 15, "col":9, "size_x":9, "size_y":6}
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
    ROUND(COUNT(CASE WHEN order_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Repeat Rate %",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV",
    ROUND(AVG(recency_days), 0) as "Avg Recency (days)"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
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
{"row": 22, "col":0, "size_x":18, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** monthly-cohort · **Scope:** scope_retail · **Caveats:** Cohort rolling
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Phan tich Cohort


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Cohort 12 tháng: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '12 months')::DATE, '%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%m/%Y') ||
  '  ·  (tháng ' || strftime(date_trunc('month', current_date)::DATE, '%m/%Y') || ' đang tích lũy)'
  AS "Chu kỳ báo cáo"
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
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Examine cohort retention matrix — identify drop-off patterns

# Examine cohort retention matrix — identify drop-off patterns

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Track revenue by cohort — are recent cohorts contributing enough?

# Track revenue by cohort — are recent cohorts contributing enough?

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Compare new vs returning — revenue dependency and growth quality

# Compare new vs returning — revenue dependency and growth quality

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 18, "size_y": 1 }
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
      AND date_diff('month', c.first_order_date, o.ordered_at) = 1
      AND o.scope_sales
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
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
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
      AND date_diff('month', c.first_order_date, o.ordered_at) = 1
      AND o.scope_sales
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
{ "row": 3, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Orders per Customer

Average number of orders among paying customers, with MoM comparison.

```sql
WITH current_period AS (
    SELECT ROUND(AVG(order_count), 1) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND order_count > 0
),
previous_period AS (
    SELECT ROUND(AVG(order_count), 1) as value
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND order_count > 0
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
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Returning Revenue Ratio

Percentage of total revenue coming from returning customers.

```sql
SELECT
    ROUND(
        SUM(CASE
            WHEN date_trunc('month', o.ordered_at) != date_trunc('month', c.first_order_date)
            THEN o.net_revenue ELSE 0
        END) * 100.0 / NULLIF(SUM(o.net_revenue), 0), 1
    ) as "Returning Revenue %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.ordered_at < date_trunc('month', current_date)
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
{ "row": 3, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Cohort Retention Heatmap

Percentage of customers returning in subsequent months after first purchase (12-month lookback). Pre-pivoted in SQL — native SQL cards don't support display:pivot.

```sql
WITH cohort_first_orders AS (
    -- First scope_sales order per customer — ensures M0 is always 100%
    SELECT
        customer_key,
        date_trunc('month', MIN(ordered_at))::date AS cohort_month
    FROM fact_orders
    WHERE scope_sales
      AND customer_key IS NOT NULL
    GROUP BY 1
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_key) AS original_size
    FROM cohort_first_orders
    WHERE cohort_month >= (date_trunc('month', current_date) - INTERVAL '12 months')::date
    GROUP BY 1
),
retention_activity AS (
    SELECT
        co.cohort_month,
        date_diff('month', co.cohort_month, date_trunc('month', o.ordered_at)::date) AS month_number,
        COUNT(DISTINCT co.customer_key) AS active_customers
    FROM cohort_first_orders co
    JOIN fact_orders o ON co.customer_key = o.customer_key
    WHERE co.cohort_month >= (date_trunc('month', current_date) - INTERVAL '12 months')::date
      AND o.scope_sales
      AND date_trunc('month', o.ordered_at)::date >= co.cohort_month
    GROUP BY 1, 2
),
retention_pct AS (
    SELECT
        strftime(r.cohort_month, '%Y-%m') AS cohort,
        r.month_number,
        ROUND(CAST(r.active_customers AS FLOAT) / s.original_size * 100, 1) AS ret_pct
    FROM retention_activity r
    JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
    WHERE r.month_number BETWEEN 0 AND 11
)
SELECT
    cohort                                              AS "Cohort",
    MAX(CASE WHEN month_number = 0  THEN ret_pct END)  AS "M0",
    MAX(CASE WHEN month_number = 1  THEN ret_pct END)  AS "M1",
    MAX(CASE WHEN month_number = 2  THEN ret_pct END)  AS "M2",
    MAX(CASE WHEN month_number = 3  THEN ret_pct END)  AS "M3",
    MAX(CASE WHEN month_number = 4  THEN ret_pct END)  AS "M4",
    MAX(CASE WHEN month_number = 5  THEN ret_pct END)  AS "M5",
    MAX(CASE WHEN month_number = 6  THEN ret_pct END)  AS "M6",
    MAX(CASE WHEN month_number = 7  THEN ret_pct END)  AS "M7",
    MAX(CASE WHEN month_number = 8  THEN ret_pct END)  AS "M8",
    MAX(CASE WHEN month_number = 9  THEN ret_pct END)  AS "M9",
    MAX(CASE WHEN month_number = 10 THEN ret_pct END)  AS "M10",
    MAX(CASE WHEN month_number = 11 THEN ret_pct END)  AS "M11"
FROM retention_pct
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11"],
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
{ "row": 7, "col": 0, "size_x": 18, "size_y": 9 }
```

---

#### ❓ Question: Revenue by Cohort (Layer Cake)

Total revenue by acquisition cohort over time — shows legacy vs new contribution.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as revenue_month,
    strftime(date_trunc('month', c.first_order_date), '%Y-%m') as cohort,
    SUM(o.net_revenue) as revenue
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '12 months'
  AND o.ordered_at < date_trunc('month', current_date)
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
{ "row": 17, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: New vs Returning Revenue (6M)

Monthly revenue split by new customers (first order month) vs returning customers.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as month,
    CASE
        WHEN date_trunc('month', o.ordered_at) = date_trunc('month', c.first_order_date)
        THEN 'New Customer'
        ELSE 'Returning Customer'
    END as customer_type,
    SUM(o.net_revenue) as revenue
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.ordered_at < date_trunc('month', current_date)
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
{ "row": 24, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New vs Returning Customers (6M)

Monthly count of new vs returning purchasers.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as month,
    CASE
        WHEN date_trunc('month', o.ordered_at) = date_trunc('month', c.first_order_date)
        THEN 'New Customer'
        ELSE 'Returning Customer'
    END as customer_type,
    COUNT(DISTINCT c.customer_id) as customers
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.ordered_at < date_trunc('month', current_date)
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
{ "row": 24, "col": 9, "size_x": 9, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** monthly-cohort · **Scope:** scope_retail · **Caveats:** Cohort rolling
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Hanh vi & Reactivation


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Reactivation 6 tháng: ' ||
  strftime((current_date - INTERVAL '6 months')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Dự báo: tuần ' || strftime(current_date, '%W/%Y') || ' & tháng ' || strftime(current_date, '%m/%Y')
  AS "Chu kỳ báo cáo"
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
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Examine purchase frequency — distribution shape and conversion opportunity

# Examine purchase frequency — distribution shape and conversion opportunity

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Track reactivation performance — is win-back ROI improving?

# Track reactivation performance — is win-back ROI improving?

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Prioritize at-risk outreach — high-value customers needing action NOW

# Prioritize at-risk outreach — high-value customers needing action NOW

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Avg Days Between Purchases

Hero metric — average inter-purchase gap for repeat customers, with MoM comparison.

```sql
WITH purchase_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.ordered_at) OVER (PARTITION BY o.customer_key ORDER BY o.ordered_at) AS DATE),
            CAST(o.ordered_at AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
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
            CAST(LAG(o.ordered_at) OVER (PARTITION BY o.customer_key ORDER BY o.ordered_at) AS DATE),
            CAST(o.ordered_at AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND c.customer_id != 'Unknown'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
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
    "column_settings": {
      "Avg Gap (days)": {
        "suffix": " days"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Reactivated Customers (Last Month)

Customers who returned after 30+ days gap, with MoM comparison.

```sql
WITH reactivated_current AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT customer_key, MAX(ordered_at) as prev_order
        FROM fact_orders
        WHERE scope_sales
          AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
        GROUP BY 1
    ) prev ON o.customer_key = prev.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.ordered_at < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      AND date_diff('day', CAST(prev.prev_order AS DATE), CAST(o.ordered_at AS DATE)) > 30
      [[AND c.value_group = {{segment}}]]
),
reactivated_prev AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT customer_key, MAX(ordered_at) as prev_order
        FROM fact_orders
        WHERE scope_sales
          AND ordered_at < date_trunc('month', current_date) - INTERVAL '2 months'
        GROUP BY 1
    ) prev ON o.customer_key = prev.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
      AND c.customer_id != 'Unknown'
      AND date_diff('day', CAST(prev.prev_order AS DATE), CAST(o.ordered_at AS DATE)) > 30
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
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: At-Risk Customers Count

Count of customers in At Risk status (31-90 days since last purchase).

```sql
SELECT
    COUNT(*) as "At Risk"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND customer_status = 'At Risk'
  AND order_count > 0
  [[AND value_group = {{segment}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: One-Time Buyer Rate

Percentage of customers with exactly 1 order — conversion opportunity. Lower is better.

```sql
-- Snapshot-driven MoM: orders_to_date = 1 as-of each month-end snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN orders_to_date = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      [[AND s.value_group = {{segment}}]]
),
previous_period AS (
    SELECT
        ROUND(
            COUNT(CASE WHEN orders_to_date = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
        ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      [[AND s.value_group = {{segment}}]]
)
SELECT
    c.value AS "One-Time %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "One-Time %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Purchase Frequency Distribution

How many orders do customers typically place? Understand one-time vs repeat behavior.

```sql
WITH total AS (
    SELECT COUNT(*) AS cnt
    FROM dim_customers
    WHERE order_count > 0
      AND customer_id != 'Unknown'
      [[AND value_group = {{segment}}]]
)
SELECT
    CASE
        WHEN order_count = 1 THEN '1 order'
        WHEN order_count = 2 THEN '2 orders'
        WHEN order_count = 3 THEN '3 orders'
        WHEN order_count BETWEEN 4 AND 5 THEN '4-5 orders'
        WHEN order_count BETWEEN 6 AND 10 THEN '6-10 orders'
        ELSE '11+ orders'
    END as "Order Count",
    COUNT(*) as "Customers",
    ROUND(
        COUNT(*) * 100.0 / NULLIF((SELECT cnt FROM total), 0), 1
    ) as "% of Total"
FROM dim_customers
WHERE order_count > 0
  AND customer_id != 'Unknown'
  [[AND value_group = {{segment}}]]
GROUP BY 1
ORDER BY MIN(order_count)
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
{ "row": 7, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Days Between Purchases Distribution

For repeat customers, how long between purchases? Helps set reactivation timing.

```sql
WITH purchase_gaps AS (
    SELECT
        o.customer_key,
        date_diff('day',
            CAST(LAG(o.ordered_at) OVER (PARTITION BY o.customer_key ORDER BY o.ordered_at) AS DATE),
            CAST(o.ordered_at AS DATE)
        ) as days_between
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
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
{ "row": 7, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Reactivation Trend (6M)

Monthly count of reactivated customers (returned after 30+ day gap) with revenue contribution.

```sql
WITH reactivated AS (
    SELECT
        date_trunc('month', o.ordered_at)::date as month,
        o.customer_key,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    JOIN (
        SELECT
            customer_key,
            ordered_at,
            LAG(ordered_at) OVER (PARTITION BY customer_key ORDER BY ordered_at) as prev_order
        FROM fact_orders
        WHERE scope_sales
    ) gaps ON o.customer_key = gaps.customer_key
        AND o.ordered_at = gaps.ordered_at
    WHERE o.scope_sales
      AND o.is_active_order
      AND gaps.prev_order IS NOT NULL
      AND date_diff('day', CAST(gaps.prev_order AS DATE), CAST(o.ordered_at AS DATE)) > 30
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND o.ordered_at < date_trunc('month', current_date)
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
{ "row": 14, "col": 0, "size_x": 18, "size_y": 6 }
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
    order_count as "Orders"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND customer_status = 'At Risk'
  AND order_count > 0
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
{ "row": 21, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### 📝 Text: P3 Predictive signals — overdue customers and upcoming purchase forecast

# P3 Predictive signals — overdue customers and upcoming purchase forecast

```json metabase-pos
{ "row": 29, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: OVERDUE Customers — Count and Value at Risk

Retail customers whose predicted next purchase date has already passed (`next_purchase_signal = 'OVERDUE'`). High value at risk requires immediate outreach.

```sql
SELECT
    COUNT(*) AS "OVERDUE Customers",
    SUM(lifetime_value) AS "Total LTV at Risk",
    ROUND(AVG(lifetime_value), 0) AS "Avg LTV",
    ROUND(AVG(recency_days), 0) AS "Avg Days Since Last Order"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND next_purchase_signal = 'OVERDUE'
  [[AND value_group = {{segment}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "OVERDUE Customers": {},
      "Total LTV at Risk": { "number_style": "currency", "currency": "VND", "compact": true },
      "Avg LTV":           { "number_style": "currency", "currency": "VND", "compact": true },
      "Avg Days Since Last Order": { "suffix": " days" }
    }
  }
}
```

```json metabase-pos
{ "row": 30, "col": 0, "size_x": 9, "size_y": 3 }
```

#### ❓ Question: Next Purchase Signal by Segment

Count of retail customers by `next_purchase_signal` within each value tier — prioritize OVERDUE segments for reactivation.

```sql
SELECT
    COALESCE(next_purchase_signal, 'N/A (1-time buyer)') AS "Signal",
    value_group AS "Segment",
    COUNT(*) AS "Customers",
    SUM(lifetime_value) AS "Total LTV"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  [[AND value_group = {{segment}}]]
GROUP BY 1, 2
ORDER BY
    CASE "Signal"
        WHEN 'OVERDUE'  THEN 1
        WHEN 'DUE_SOON' THEN 2
        WHEN 'ON_TRACK' THEN 3
        ELSE 4
    END,
    CASE value_group
        WHEN 'VALUE_VIP'    THEN 1
        WHEN 'VALUE_GOLD'   THEN 2
        WHEN 'VALUE_SILVER' THEN 3
        ELSE 4
    END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Total LTV": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Signal"],
        "type": "single",
        "operator": "=",
        "value": "OVERDUE",
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Signal"],
        "type": "single",
        "operator": "=",
        "value": "DUE_SOON",
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 30, "col": 9, "size_x": 9, "size_y": 8 }
```

#### ❓ Question: Upcoming Predicted Purchases — This Week

Retail customers whose `predicted_next_purchase_date` falls within the next 7 days — proactive engagement window.

```sql
SELECT
    COUNT(*) AS "Purchasing This Week",
    SUM(lifetime_value) AS "Total LTV",
    ROUND(AVG(avg_order_spend), 0) AS "Expected Avg Order Value"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND predicted_next_purchase_date IS NOT NULL
  AND predicted_next_purchase_date BETWEEN current_date AND current_date + INTERVAL '7 days'
  [[AND value_group = {{segment}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Purchasing This Week":      {},
      "Total LTV":                 { "number_style": "currency", "currency": "VND", "compact": true },
      "Expected Avg Order Value":  { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 33, "col": 0, "size_x": 9, "size_y": 3 }
```

#### ❓ Question: Upcoming Predicted Purchases — This Month

Retail customers whose `predicted_next_purchase_date` falls within the next 30 days — pipeline visibility for the month.

```sql
SELECT
    COUNT(*) AS "Purchasing This Month",
    SUM(lifetime_value) AS "Total LTV",
    ROUND(AVG(avg_order_spend), 0) AS "Expected Avg Order Value"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND predicted_next_purchase_date IS NOT NULL
  AND predicted_next_purchase_date BETWEEN current_date AND current_date + INTERVAL '30 days'
  [[AND value_group = {{segment}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Purchasing This Month":     {},
      "Total LTV":                 { "number_style": "currency", "currency": "VND", "compact": true },
      "Expected Avg Order Value":  { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 36, "col": 0, "size_x": 9, "size_y": 3 }
```

#### ❓ Question: OVERDUE Customer Watchlist

OVERDUE customers sorted by LTV — immediate win-back priority list.

```sql
SELECT
    full_name AS "Customer",
    phone AS "Phone",
    value_group AS "Segment",
    last_order_date AS "Last Order",
    recency_days AS "Days Since",
    predicted_next_purchase_date AS "Was Expected",
    lifetime_value AS "LTV",
    avg_order_spend AS "Avg Order Value"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND next_purchase_signal = 'OVERDUE'
  [[AND value_group = {{segment}}]]
ORDER BY lifetime_value DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "LTV":             { "number_style": "currency", "currency": "VND", "compact": true },
      "Avg Order Value": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Days Since"],
        "type": "range",
        "colors": ["#F9D45C", "#EF8C8C"],
        "min_type": "custom",
        "min_value": 30,
        "max_type": "custom",
        "max_value": 120
      },
      {
        "columns": ["LTV"],
        "type": "single",
        "operator": ">=",
        "value": 5000000,
        "color": "#7172AD",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 39, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** monthly-cohort · **Scope:** scope_retail · **Caveats:** Cohort rolling
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


# 📘 Blueprint: Customer Retention Dashboard

> **Target Collection:** `Marketing & Customers`
> **Role:** Customer Success / Executives
> **Archetype:** Operational Cockpit + Analytical

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Customer Retention & Lifecycle

**Description**: Strategic retention analytics — repeat purchase rates, churn trends with targets, cohort retention heatmap, revenue layer cake, purchase frequency distribution, and reactivation tracking.

---

#### ❓ Question: Repeat Purchase Rate

Percentage of customers who have made more than one purchase.

```sql
SELECT
    ROUND(
        COUNT(CASE WHEN total_orders_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
    ) as "Repeat Rate %"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Repeat Rate %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: Avg Orders per Customer

Average number of orders among customers who have purchased.

```sql
SELECT
    ROUND(AVG(total_orders_count), 1) as "Avg Orders"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 5, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: Avg Customer Lifespan

Average days between first and last order for repeat customers.

```sql
SELECT
    ROUND(AVG(lifespan_days), 0) as "Avg Lifespan (days)"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 1
  AND lifespan_days > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Avg Lifespan (days)": { "suffix": " days" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Churn Rate (Current)

Percentage of customers who are churned (90+ days inactive) among all customers with orders.

```sql
SELECT
    ROUND(
        COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    ) as "Churn Rate %"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND total_orders_count > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Churn Rate %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Churn Rate Trend (6M)

Monthly churn rate with goal line — target below 40%.

_Note: Approximates churn date as 90 days after last order._

```sql
SELECT
    date_trunc('month', last_order_date + INTERVAL '90' DAY)::date as month,
    COUNT(customer_id) as churned_customers,
    ROUND(
        COUNT(customer_id) * 100.0 / NULLIF(
            (SELECT COUNT(*) FROM dim_customers WHERE total_orders_count > 0), 0
        ), 1
    ) as "Churn Rate %"
FROM dim_customers
WHERE customer_status = 'Churned'
  AND (last_order_date + INTERVAL '90' DAY) >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND (last_order_date + INTERVAL '90' DAY) < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["churned_customers"],
    "graph.colors": ["#EF8C8C"],
    "graph.goal_value": 50,
    "graph.show_goal": true,
    "graph.goal_label": "Target < 50 churned/month"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

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
GROUP BY 1
ORDER BY MIN(total_orders_count)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Order Count"],
    "graph.metrics": ["Customers"],
    "graph.colors": ["#A989C5"]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Cohort Retention Heatmap

Percentage of customers returning in subsequent months after their first purchase (12-month lookback).

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
    GROUP BY 1, 2
)
SELECT
    r.cohort_month as "Cohort",
    r.month_number as "Month #",
    s.original_size as "Cohort Size",
    r.active_customers as "Active",
    ROUND(CAST(r.active_customers AS FLOAT) / s.original_size * 100, 1) as "Retention %"
FROM retention_activity r
JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
WHERE r.month_number <= 12
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": true,
    "table.pivot_column": "Month #",
    "table.cell_column": "Retention %",
    "table.columns": [
      { "name": "Cohort", "enabled": true },
      { "name": "Month #", "enabled": true },
      { "name": "Retention %", "enabled": true }
    ]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### ❓ Question: Revenue by Cohort (Layer Cake)

Total revenue generated by each acquisition cohort over time — shows how recent cohorts contribute vs legacy customers.

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as revenue_month,
    date_trunc('month', c.first_order_date)::date as cohort,
    SUM(o.net_revenue) as revenue
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '12 months'
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
    "stackable.stack_type": "stacked"
  }
}
```

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Repeat Purchase Rate Trend (6M)

Monthly trend of the percentage of customers making a repeat purchase.

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
    "graph.colors": ["#84BB4C"]
  }
}
```

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New vs Returning Revenue Split (6M)

Monthly revenue contribution from new customers (first order) vs returning customers.

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
    "graph.colors": ["#509EE3", "#84BB4C"]
  }
}
```

```json metabase-pos
{ "row": 23, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Days Between Purchases Distribution

For repeat customers, how long between purchases? Helps set reactivation timing.

```sql
WITH purchase_gaps AS (
    SELECT
        customer_key,
        order_timestamp,
        LAG(order_timestamp) OVER (PARTITION BY customer_key ORDER BY order_timestamp) as prev_order,
        date_diff('day',
            CAST(LAG(order_timestamp) OVER (PARTITION BY customer_key ORDER BY order_timestamp) AS DATE),
            CAST(order_timestamp AS DATE)
        ) as days_between
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
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
    "graph.colors": ["#88BF4D"]
  }
}
```

```json metabase-pos
{ "row": 29, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Reactivation Tracking (6M)

Monthly count of customers who were At Risk/Churned but placed a new order — measures win-back success.

```sql
WITH customer_monthly_status AS (
    SELECT
        date_trunc('month', o.order_timestamp)::date as order_month,
        o.customer_key,
        c.recency_days,
        MIN(o.order_timestamp) as first_order_in_month
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND o.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1, 2, 3
),
reactivated AS (
    SELECT
        cms.order_month,
        cms.customer_key
    FROM customer_monthly_status cms
    JOIN fact_orders prev ON cms.customer_key = prev.customer_key
        AND prev.order_timestamp < cms.first_order_in_month
    GROUP BY 1, 2
    HAVING date_diff('day',
        CAST(MAX(prev.order_timestamp) AS DATE),
        CAST(MIN(cms.first_order_in_month) AS DATE)
    ) > 30
)
SELECT
    order_month as month,
    COUNT(DISTINCT customer_key) as "Reactivated Customers"
FROM reactivated
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Reactivated Customers"],
    "graph.colors": ["#F9A825"]
  }
}
```

```json metabase-pos
{ "row": 29, "col": 9, "size_x": 9, "size_y": 6 }
```

# 📘 Blueprint: Customer Operational Dashboard

> **Target Collection:** `Marketing & Customers`
> **Role:** Customer Success / Sales Ops
> **Archetype:** Operational Cockpit

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Customer Operational Dashboard

**Description**: Daily operational cockpit — customer health KPIs with MoM trends, segment distribution, acquisition tracking, geographic insights, and actionable watchlists for VIP care and churn prevention.

---

#### ❓ Question: Monthly Active Customers (MAU)

Customers with at least one order in the last 30 days.

```sql
SELECT COUNT(DISTINCT customer_id) as "Active Customers"
FROM dim_customers
WHERE recency_days <= 30
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: New Customers (MTD)

New customers acquired this month.

```sql
SELECT COUNT(*) as "New Customers"
FROM dim_customers
WHERE created_at >= date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 5, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: At Risk Customers

Customers with no purchase in 31–90 days.

```sql
SELECT COUNT(*) as "At Risk"
FROM dim_customers
WHERE customer_status = 'At Risk'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Churned Customers

Customers with no purchase for over 90 days.

```sql
SELECT COUNT(*) as "Churned"
FROM dim_customers
WHERE customer_status = 'Churned'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Customer Status Summary (MoM)

Month-over-month comparison of customer status distribution.

```sql
WITH this_month AS (
    SELECT
        customer_status,
        COUNT(*) as customers,
        SUM(lifetime_value) as total_ltv
    FROM dim_customers
    WHERE last_order_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND last_order_date < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT
        customer_status,
        COUNT(*) as customers,
        SUM(lifetime_value) as total_ltv
    FROM dim_customers
    WHERE last_order_date >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND last_order_date < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    COALESCE(tm.customer_status, lm.customer_status) as "Status",
    COALESCE(tm.customers, 0) as "This Month",
    COALESCE(lm.customers, 0) as "Last Month",
    CASE WHEN COALESCE(lm.customers, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tm.customers, 0) - lm.customers) * 100.0 / lm.customers, 1) END as "MoM %",
    COALESCE(tm.total_ltv, 0) as "LTV (This Month)"
FROM this_month tm
FULL OUTER JOIN last_month lm ON tm.customer_status = lm.customer_status
ORDER BY COALESCE(tm.customers, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "LTV (This Month)": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Customer Segment Distribution

Breakdown by value segment (VIP / Loyal / Regular).

```sql
SELECT
    customer_segment as "Segment",
    COUNT(*) as "Customers",
    SUM(lifetime_value) as "Total LTV",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV",
    ROUND(AVG(total_orders_count), 1) as "Avg Orders",
    ROUND(AVG(recency_days), 0) as "Avg Recency (days)"
FROM dim_customers
WHERE customer_id != 'Unknown'
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Total LTV": { "number_style": "currency", "currency": "VND" },
      "Avg LTV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Customer Acquisition Trend (6M)

Monthly new customer acquisition over 6 months with goal line.

```sql
SELECT
    date_trunc('month', created_at)::date as month,
    COUNT(*) as "New Customers"
FROM dim_customers
WHERE created_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND created_at < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["New Customers"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Customer Status Trend (6M)

Monthly evolution of Active / At Risk / Churned customers.

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as month,
    COUNT(DISTINCT CASE WHEN date_diff('day', CAST(o.order_timestamp AS DATE), current_date) <= 30 THEN o.customer_key END) as "Active",
    COUNT(DISTINCT CASE WHEN date_diff('day', CAST(o.order_timestamp AS DATE), current_date) BETWEEN 31 AND 90 THEN o.customer_key END) as "At Risk",
    COUNT(DISTINCT CASE WHEN date_diff('day', CAST(o.order_timestamp AS DATE), current_date) > 90 THEN o.customer_key END) as "Churned"
FROM fact_orders o
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Active", "At Risk", "Churned"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#84BB4C", "#F9A825", "#EF8C8C"]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: New Customers by Channel

Which channels bring in the most new customers this month?

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.customer_key) as "New Customers",
    SUM(o.net_revenue) as "First-Order Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE cust.first_order_date >= date_trunc('month', current_date)
  AND o.order_timestamp = cust.first_order_date
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["New Customers"],
    "graph.x_axis.axis_enabled": true,
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Customer Geographic Distribution

Top provinces by customer count.

```sql
SELECT
    COALESCE(NULLIF(province, ''), 'Unknown') as "Province",
    COUNT(*) as "Customers",
    SUM(lifetime_value) as "Total LTV",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Province"],
    "graph.metrics": ["Customers"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 15, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: VIP Customer Watchlist

Top VIP customers sorted by recency — prioritize outreach for those becoming inactive.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    total_orders_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Since Last Order",
    customer_status as "Status",
    last_order_date as "Last Order"
FROM dim_customers
WHERE customer_segment = 'VIP'
ORDER BY recency_days DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "LTV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: At Risk Reactivation Priority

At-risk customers ranked by lifetime value — highest value = highest reactivation priority.

```sql
SELECT
    full_name as "Customer",
    phone as "Phone",
    email as "Email",
    total_orders_count as "Orders",
    lifetime_value as "LTV",
    recency_days as "Days Inactive",
    last_order_date as "Last Order"
FROM dim_customers
WHERE customer_status = 'At Risk'
ORDER BY lifetime_value DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "LTV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: RFM Segment Health Matrix

Cross-tabulation of customer status × segment — shows where value is concentrated and at risk.

```sql
SELECT
    customer_segment as "Segment",
    COUNT(*) as "Total",
    COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) as "Active",
    COUNT(CASE WHEN customer_status = 'At Risk' THEN 1 END) as "At Risk",
    COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) as "Churned",
    ROUND(
        COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    ) as "Active %",
    SUM(CASE WHEN customer_status = 'At Risk' THEN lifetime_value ELSE 0 END) as "At-Risk LTV"
FROM dim_customers
WHERE customer_id != 'Unknown'
GROUP BY 1
ORDER BY
    CASE customer_segment WHEN 'VIP' THEN 1 WHEN 'Loyal' THEN 2 ELSE 3 END
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "At-Risk LTV": { "number_style": "currency", "currency": "VND" },
      "Active %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 33, "col": 0, "size_x": 18, "size_y": 5 }
```

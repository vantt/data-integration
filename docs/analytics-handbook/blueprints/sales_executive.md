# 📘 Sales Analytics Blueprint

**Playbook**: [Sales Executive Overview](../playbooks/sales_executive.md)

This document defines the core sales dashboards and metrics.

## 📂 Collection: Sales Analytics

This collection contains all top-level sales reports for executives.

### 🧊 Model: Fact Orders

The central table for all order-related analysis.

```sql
SELECT * FROM fact_orders
```

### 🧊 Model: Sales Actual vs Target

This model joins `fact_targets` and `fact_orders` (aggregated) to enable comparison.

```sql
WITH targets AS (
    SELECT
        date_trunc('month', target_date) as month_start_date,
        branch_key, -- Using Key directly for now
        channel_key,
        SUM(target_val) as target_revenue
    FROM fact_targets
    GROUP BY 1, 2, 3
),

actuals AS (
    SELECT
        date_trunc('month', order_timestamp) as month_start_date,
        branch_location_key, -- Need JOIN to get Code/Name to match Targets
        channel_key,
        SUM(gmv) as actual_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1, 2, 3
)

SELECT
    COALESCE(t.month_start_date, a.month_start_date) as month_start_date,
    COALESCE(t.target_revenue, 0) as target_revenue,
    COALESCE(a.actual_revenue, 0) as actual_revenue,
    COALESCE(a.actual_revenue, 0) / NULLIF(t.target_revenue, 0) as achievement_rate
FROM targets t
FULL OUTER JOIN actuals a
    ON t.month_start_date = a.month_start_date
    -- Note: complex logic might be needed for Branch/Channel mapping in SQL
```

#### 📏 Metric: Total Revenue

Gross Merchandise Value (GMV).

**Domain Reference**: [GMV](../domains/sales.md#1-gmv-gross-merchandise-value)

```sql --metric
SUM(gmv)
```

---

### 🖥️ Dashboard: Daily Sales Performance

**Description**: High-level daily overview of sales performance.

#### ❓ Question: Daily Revenue Trend

Line chart showing revenue over the last 30 days.

**Domain Reference**: [GMV](../domains/sales.md#1-gmv-gross-merchandise-value)

```sql
SELECT
    order_timestamp::date as order_date,
    SUM(gmv) as revenue
FROM fact_orders
WHERE order_timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "x_axis": "order_date",
  "y_axis": "revenue",
  "visualization_settings": {
    "graph.dimensions": ["order_date"],
    "graph.metrics": ["revenue"]
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: Sales by Channel

Breakdown of revenue by sales channel.

**Domain Reference**: [Sales by Channel](../domains/sales.md#6-sales-by-channel)

```sql
SELECT
    c.channel_name as channel,
    SUM(o.gmv) as revenue
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie"
}
```

```json metabase-pos
{
  "row": 6,
  "col": 0,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: Recent Orders

List of the latest 10 orders.

```sql
SELECT order_id, order_timestamp, gmv, c.channel_name
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
ORDER BY order_timestamp DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table"
}
```

```json metabase-pos
{
  "row": 6,
  "col": 6,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: Sales by Region

Revenue breakdown by geographic region.

**Domain Reference**: [Sales by Region](../domains/sales.md#13-sales-by-regionlocation)

```sql
SELECT
    l.branch_location_name as "Region",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_branch_location l USING (branch_location_key)
GROUP BY 1
```

```json metabase-viz
{
  "display": "map",
  "map.region": "us_states",
  "map.metric": "Revenue"
}
```

```json metabase-pos
{
  "row": 12,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: Promotion Performance

Revenue and usage count by promotion.

**Domain Reference**: [Promotion Performance](../domains/sales.md#12-promotion-performance)

```sql
SELECT
    COALESCE(p.promotion_code, 'No Promotion') as "Promotion",
    COUNT(DISTINCT o.order_id) as "Usage Count",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE p.promotion_code IS NOT NULL
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table"
}
```

```json metabase-pos
{
  "row": 12,
  "col": 12,
  "size_x": 6,
  "size_y": 6
}
```

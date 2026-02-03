# 📘 Sales Analytics Blueprint

This document defines the core sales dashboards and metrics.

## 📂 Collection: Sales Analytics

This collection contains all top-level sales reports for executives.

### 🧊 Model: Fact Orders

The central table for all order-related analysis.

```sql
SELECT * FROM fact_orders
```

#### 📏 Metric: Total Revenue

Gross Merchandise Value (GMV).

```sql --metric
SUM(total)
```

---

### 🖥️ Dashboard: Daily Sales Performance

**Description**: High-level daily overview of sales performance.

#### ❓ Question: Daily Revenue Trend

Line chart showing revenue over the last 30 days.

```sql
SELECT
    created_on::date as order_date,
    SUM(total) as revenue
FROM fact_orders
WHERE created_on >= CURRENT_DATE - INTERVAL '30 days'
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

```sql
SELECT
    channel,
    SUM(total) as revenue
FROM fact_orders
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
SELECT order_id, created_on, total, channel
FROM fact_orders
ORDER BY created_on DESC
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

# ≡ƒôÿ Sales Analytics Blueprint

**Playbook**: [Sales Executive Overview](../playbooks/sales_executive.md)

This document defines the core sales dashboards and metrics.

## ≡ƒôé Collection: Sales Analytics

This collection contains all top-level sales reports for executives.

### ≡ƒºè Model: Fact Orders

The central table for all order-related analysis.

```sql
SELECT * FROM fact_orders
```

#### ≡ƒôÅ Metric: Total Revenue

Gross Merchandise Value (GMV).

**Domain Reference**: [GMV](../domains/sales.md#1-gmv-gross-merchandise-value)

```sql --metric
SUM(total)
```

---

### ≡ƒûÑ∩╕Å Dashboard: Daily Sales Performance

**Description**: High-level daily overview of sales performance.

#### Γ¥ô Question: Daily Revenue Trend

Line chart showing revenue over the last 30 days.

**Domain Reference**: [GMV](../domains/sales.md#1-gmv-gross-merchandise-value)

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

#### Γ¥ô Question: Sales by Channel

Breakdown of revenue by sales channel.

**Domain Reference**: [Sales by Channel](../domains/sales.md#6-sales-by-channel)

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

#### Γ¥ô Question: Recent Orders

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

#### Γ¥ô Question: Sales by Region

Revenue breakdown by geographic region.

**Domain Reference**: [Sales by Region](../domains/sales.md#13-sales-by-regionlocation)

```sql
SELECT
    l.region as "Region",
    SUM(o.total) as "Revenue"
FROM fact_orders o
JOIN dim_locations l USING (location_id)
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

#### Γ¥ô Question: Promotion Performance

Revenue and usage count by promotion.

**Domain Reference**: [Promotion Performance](../domains/sales.md#12-promotion-performance)

```sql
SELECT
    pr.promotion_name as "Promotion",
    COUNT(DISTINCT o.order_id) as "Usage Count",
    SUM(o.total) as "Revenue"
FROM orders o
JOIN promotion_redemptions pr USING (order_id)
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

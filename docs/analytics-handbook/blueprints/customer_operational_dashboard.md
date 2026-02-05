# 📘 Blueprint: Customer Operational Dashboard

> **Target Collection:** `Customer Operations`
> **Role:** Customer Success / Sales Ops

## 📂 Collection: Customer Operations

Operational dashboards for managing customer relationships.

### 🖥️ Dashboard: Customer Operational Dashboard

Daily tracking of customer health, growth, and risks.

#### ❓ Question: Monthly Active Users (MAU)

Users active in the last 30 days.

```sql
SELECT count(distinct customer_id)
FROM dim_customers
WHERE recency_days <= 30
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 4,
  "size_y": 4
}
```

#### ❓ Question: New Customers (MTD)

New customers acquired this month.

```sql
SELECT count(*)
FROM dim_customers
WHERE created_at >= date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 4,
  "size_x": 4,
  "size_y": 4
}
```

#### ❓ Question: At Risk Customers

Customers who have not purchased in 31-90 days.

```sql
SELECT count(*)
FROM dim_customers
WHERE customer_status = 'At Risk'
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 8,
  "size_x": 4,
  "size_y": 4
}
```

#### ❓ Question: Customer Growth Trend

Monthly new customer acquisition.

```sql
SELECT
    date_trunc('month', created_at) as month,
    count(*) as new_customers
FROM dim_customers
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["new_customers"]
  }
}
```

```json metabase-pos
{
  "row": 4,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: Customer Status Distribution

Breakdown of active vs risk vs churned.

```sql
SELECT customer_status, count(*) as count
FROM dim_customers
GROUP BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["customer_status"],
    "graph.metrics": ["count"]
  }
}
```

```json metabase-pos
{
  "row": 10,
  "col": 0,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: VIP Customer List

High value customers for priority support.

```sql
SELECT
    full_name,
    phone,
    total_orders_count,
    lifetime_value,
    last_order_date
FROM dim_customers
WHERE customer_segment = 'VIP'
LIMIT 100
```

```json metabase-viz
{
  "display": "table"
}
```

```json metabase-pos
{
  "row": 16,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: At Risk Watchlist

Customers needing reactivation.

```sql
SELECT
    full_name,
    phone,
    recency_days,
    lifetime_value
FROM dim_customers
WHERE customer_status = 'At Risk'
LIMIT 100
```

```json metabase-viz
{
  "display": "table"
}
```

```json metabase-pos
{
  "row": 22,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

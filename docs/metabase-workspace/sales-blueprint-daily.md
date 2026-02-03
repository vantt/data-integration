# 📘 Daily Sales Performance Blueprint

📖 **Playbook**: [sales-playbook.md#daily-sales-dashboard]

This blueprint creates a real-time sales monitoring dashboard for daily operations.

## 📂 Collection: Daily Operations

This collection contains operational dashboards updated in real-time.

### 🧊 Model: Today's Orders

Orders from the current date for real-time monitoring.

```sql
SELECT * FROM fact_orders
WHERE date(order_timestamp) = current_date
```

---

### 🖥️ Dashboard: Daily Sales Performance

**Description**: Real-time monitoring of today's sales performance with hourly breakdown.

#### ❓ Question: Daily Metrics Summary

Key metrics for today's performance.

```sql
SELECT
    count(distinct o.order_id) as "Total Orders",
    coalesce(sum(o.gmv), 0) as "Total Revenue",
    case when count(distinct o.order_id) = 0 then 0
         else sum(o.gmv) / count(distinct o.order_id) end as "AOV",
    count(distinct case when date(c.first_order_date) = current_date then o.customer_key end) as "New Customers",
    count(distinct case when date(c.first_order_date) < current_date then o.customer_key end) as "Return Customers"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "table.cell_column": "Total Revenue"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 4
}
```

#### ❓ Question: Hourly Sales Trend

Compare today's hourly performance with yesterday.

```sql
WITH current_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_today
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
    GROUP BY 1
),
previous_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_yesterday
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    COALESCE(c.hour_of_day, p.hour_of_day) as hour_of_day,
    COALESCE(c.sales_today, 0) as sales_today,
    COALESCE(p.sales_yesterday, 0) as sales_yesterday
FROM current_sales c
FULL OUTER JOIN previous_sales p ON c.hour_of_day = p.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "graph.dimensions": ["hour_of_day"],
  "graph.metrics": ["sales_today", "sales_yesterday"],
  "graph.colors": ["#509EE3", "#CCCCCC"]
}
```

```json metabase-pos
{
  "row": 4,
  "col": 0,
  "size_x": 12,
  "size_y": 8
}
```

#### ❓ Question: Top Channels Today

Revenue breakdown by sales channel.

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.gmv) as "Revenue",
    COUNT(distinct o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "pie.dimension": "Channel",
  "pie.metric": "Revenue"
}
```

```json metabase-pos
{
  "row": 4,
  "col": 12,
  "size_x": 6,
  "size_y": 8
}
```

#### ❓ Question: Top Products Today

Best selling products by revenue.

```sql
SELECT
    p.product_name as "Product",
    SUM(s.revenue) as "Revenue",
    SUM(s.quantity) as "Units Sold"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "table.column_formatting": [{
    "columns": ["Revenue"],
    "type": "currency",
    "currency": "USD"
  }]
}
```

```json metabase-pos
{
  "row": 12,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```
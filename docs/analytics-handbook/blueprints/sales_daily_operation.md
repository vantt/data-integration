# 📘 Daily Sales Performance Blueprint

📖 **Playbook**: [Daily Sales Operations] (../playbooks/sales_daily_operation.md)

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

### 🖥️ Dashboard: Daily Sales Dashboard

**Description**: Real-time monitoring of today's sales performance with hourly breakdown.

#### ❓ Question: Current Date Label

Display the date being filtered for context.

```sql
SELECT to_char(current_date, 'YYYY-MM-DD') as "Date"
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
  "size_y": 2
}
```

#### ❓ Question: Daily Metrics Summary

Key metrics for today's performance.

**Domain Reference**: [GMV (Total Revenue)](../domains/sales.md#1-gmv-gross-merchandise-value), [Orders](../domains/sales.md#3-total-orders), [AOV](../domains/sales.md#4-aov-average-order-value), [New vs Returning](../domains/sales.md#8-new-vs-returning-customers)

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
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 4
}
```

#### ❓ Question: Hourly Sales Trend

Compare today's hourly performance with yesterday.

**Domain Reference**: [Hourly Sales Trend](../domains/sales.md#5-hourly-sales-trend)

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
  "row": 6,
  "col": 0,
  "size_x": 12,
  "size_y": 8
}
```

#### ❓ Question: Top Channels Today

Revenue breakdown by sales channel.

**Domain Reference**: [Sales by Channel](../domains/sales.md#6-sales-by-channel)

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
  "row": 6,
  "col": 12,
  "size_x": 6,
  "size_y": 8
}
```

#### ❓ Question: Top Products Today

Best selling products by revenue.

**Domain Reference**: [Top Selling Products](../domains/sales.md#7-top-selling-products)

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
  "table.column_formatting": [
    {
      "columns": ["Revenue"],
      "type": "currency",
      "currency": "USD"
    }
  ]
}
```

```json metabase-pos
{
  "row": 14,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

#### ❓ Question: Payment Method Distribution

Breakdown of transaction volume by payment method.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#9-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "Payment Method",
    COUNT(*) as "Transaction Count",
    SUM(p.amount) as "Total Amount"
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
WHERE date(p.payment_timestamp) = current_date
GROUP BY 1
```

```json metabase-viz
{
  "display": "pie",
  "pie.dimension": "Payment Method",
  "pie.metric": "Transaction Count"
}
```

```json metabase-pos
{
  "row": 20,
  "col": 0,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: Hourly Heatmap

Sales intensity by Hour of Day and Day of Week.

**Domain Reference**: [Hourly Heatmap](../domains/sales.md#51-hourly-heatmap-day-of-week-analysis)

```sql
SELECT
    EXTRACT(HOUR FROM order_timestamp) as "Hour",
    EXTRACT(DOW FROM order_timestamp) as "Day of Week",
    COUNT(*) as "Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date)
GROUP BY 1, 2
ORDER BY 2, 1
```

```json metabase-viz
{
  "display": "heatmap",
  "heatmap.x_axis": "Hour",
  "heatmap.y_axis": "Day of Week",
  "heatmap.metric": "Orders"
}
```

```json metabase-pos
{
  "row": 20,
  "col": 6,
  "size_x": 12,
  "size_y": 6
}
```

# Daily Sales Performance Blueprint

**Playbook**: [Daily Sales Operations](../playbooks/sales_daily_operation.md)

This blueprint creates a real-time sales monitoring dashboard for daily operations.

## 📂 Collection: Operations > Daily Monitoring

This collection contains operational dashboards updated in real-time.

### Model: Today's Orders

Orders from the current date for real-time monitoring.

```sql
SELECT * FROM fact_orders
WHERE date(order_timestamp) = current_date
```

---

### Dashboard: Daily Sales Dashboard

**Description**: Real-time monitoring of today's sales performance with hourly breakdown and day-over-day comparisons.

#### Question: Current Date Label

Display the date being filtered for context.

```sql
SELECT strftime(current_date, '%Y-%m-%d') as "Date"
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
  "size_x": 18,
  "size_y": 2
}
```

#### Question: Daily Metrics Summary

Key metrics for today's performance with day-over-day (DoD) change vs yesterday.

**Domain Reference**: [Revenue](../domains/sales.md#1-gross-revenue-gmv), [Net Revenue](../domains/sales.md#2-net-revenue), [Orders](../domains/sales.md#4-total-orders), [AOV](../domains/sales.md#5-aov-average-order-value), [Returns](../domains/sales.md#3-return-rate--count), [Discounts](../domains/sales.md#13-discount-impact)

```sql
WITH today AS (
    SELECT
        count(distinct o.order_id) as total_orders,
        coalesce(sum(o.net_revenue), 0) as total_revenue,
        coalesce(sum(o.net_revenue), 0) as net_revenue,
        case when count(distinct o.order_id) = 0 then 0
             else sum(o.net_revenue) / count(distinct o.order_id) end as aov,
        count(case when o.fulfillment_status = 'RETURNED' then 1 end) as return_count,
        sum(coalesce(o.discount_amount, 0)) as total_discounts,
        count(distinct case when date(c.first_order_date) = current_date then o.customer_key end) as new_customers,
        count(distinct case when date(c.first_order_date) < current_date then o.customer_key end) as return_customers
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date
),
yesterday AS (
    SELECT
        count(distinct order_id) as total_orders,
        coalesce(sum(net_revenue), 0) as total_revenue,
        coalesce(sum(net_revenue), 0) as net_revenue,
        case when count(distinct order_id) = 0 then 0
             else sum(net_revenue) / count(distinct order_id) end as aov
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT
    t.total_orders as "Total Orders",
    t.total_revenue as "Total Revenue",
    t.net_revenue as "Net Revenue",
    t.aov as "AOV",
    t.return_count as "Returns",
    t.total_discounts as "Total Discounts",
    t.new_customers as "New Customers",
    t.return_customers as "Return Customers",
    case when y.total_revenue = 0 then null
         else round((t.total_revenue - y.total_revenue) * 100.0 / y.total_revenue, 1) end as "Revenue DoD %",
    case when y.total_orders = 0 then null
         else round((t.total_orders - y.total_orders) * 100.0 / y.total_orders, 1) end as "Orders DoD %",
    case when y.aov = 0 then null
         else round((t.aov - y.aov) * 100.0 / y.aov, 1) end as "AOV DoD %"
FROM today t
CROSS JOIN yesterday y
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

#### Question: Hourly Sales Trend

Compare today's hourly performance with yesterday.

**Domain Reference**: [Hourly Sales Trend](../domains/sales.md#6-hourly-sales-trend)

```sql
WITH current_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as sales_today
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
    GROUP BY 1
),
previous_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as sales_yesterday
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

#### Question: Top Channels Today

Revenue breakdown by sales channel.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.net_revenue) as "Revenue",
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

#### Question: Top Products Today

Best selling products by revenue.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

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
      "currency": "VND"
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

#### Question: Payment Method Distribution

Breakdown of transaction volume by payment method.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

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

#### Question: New vs Returning Customers

Customer acquisition breakdown for today.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    CASE
        WHEN date(c.first_order_date) = current_date THEN 'New'
        ELSE 'Returning'
    END as "Customer Type",
    COUNT(distinct o.order_id) as "Orders",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
```

```json metabase-viz
{
  "display": "bar",
  "graph.dimensions": ["Customer Type"],
  "graph.metrics": ["Orders", "Revenue"]
}
```

```json metabase-pos
{
  "row": 20,
  "col": 6,
  "size_x": 6,
  "size_y": 6
}
```

#### Question: Discount Impact Today

Discount usage and impact on revenue.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    COUNT(distinct order_id) as "Total Orders",
    COUNT(distinct case when discount_amount > 0 then order_id end) as "Discounted Orders",
    ROUND(COUNT(distinct case when discount_amount > 0 then order_id end) * 100.0
        / NULLIF(COUNT(distinct order_id), 0), 1) as "Discount Rate %",
    SUM(coalesce(discount_amount, 0)) as "Total Discounts",
    ROUND(AVG(case when discount_amount > 0
        then discount_amount * 100.0 / NULLIF(gross_revenue, 0) end), 1) as "Avg Discount %"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{
  "row": 20,
  "col": 12,
  "size_x": 6,
  "size_y": 6
}
```

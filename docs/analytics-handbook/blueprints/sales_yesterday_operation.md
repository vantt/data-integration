# Yesterday's Sales Performance Blueprint

**Playbook**: [Yesterday's Sales Operations](../playbooks/sales_yesterday_operation.md)

This blueprint creates a finalized sales review dashboard for yesterday's operations with day-over-day comparisons.

## Collection: Daily Operations

This collection contains operational dashboards. Yesterday's dashboard uses finalized (complete) data.

### Model: Yesterday's Orders

Orders from the previous date (finalized, no further changes expected).

```sql
SELECT * FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

---

### Dashboard: Yesterday's Sales Dashboard

**Description**: Finalized review of yesterday's sales performance with day-over-day comparisons.

#### Question: Yesterday Date Label

Display the date being reviewed for context.

```sql
SELECT to_char(current_date - INTERVAL '1 day', 'YYYY-MM-DD') as "Date"
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

#### Question: Yesterday's Metrics Summary

Key metrics for yesterday with day-over-day (DoD) change.

**Domain Reference**: [GMV](../domains/sales.md#1-gmv-gross-merchandise-value), [Net Revenue](../domains/sales.md#2-net-revenue), [Orders](../domains/sales.md#4-total-orders), [AOV](../domains/sales.md#5-aov-average-order-value), [Returns](../domains/sales.md#3-return-rate--count), [Discounts](../domains/sales.md#13-discount-impact)

```sql
WITH yesterday AS (
    SELECT
        count(distinct o.order_id) as total_orders,
        coalesce(sum(o.gmv), 0) as total_revenue,
        coalesce(sum(o.gmv - coalesce(o.total_discount_amount, 0)), 0) as net_revenue,
        case when count(distinct o.order_id) = 0 then 0
             else sum(o.gmv) / count(distinct o.order_id) end as aov,
        count(case when o.fulfillment_status = 'RETURNED' then 1 end) as return_count,
        sum(coalesce(o.total_discount_amount, 0)) as total_discounts,
        count(distinct case when date(c.first_order_date) = current_date - INTERVAL '1 day' then o.customer_key end) as new_customers,
        count(distinct case when date(c.first_order_date) < current_date - INTERVAL '1 day' then o.customer_key end) as return_customers
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
),
day_before AS (
    SELECT
        count(distinct order_id) as total_orders,
        coalesce(sum(gmv), 0) as total_revenue,
        coalesce(sum(gmv - coalesce(total_discount_amount, 0)), 0) as net_revenue,
        case when count(distinct order_id) = 0 then 0
             else sum(gmv) / count(distinct order_id) end as aov
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
)
SELECT
    y.total_orders as "Total Orders",
    y.total_revenue as "Total Revenue",
    y.net_revenue as "Net Revenue",
    y.aov as "AOV",
    y.return_count as "Returns",
    y.total_discounts as "Total Discounts",
    y.new_customers as "New Customers",
    y.return_customers as "Return Customers",
    case when d.total_revenue = 0 then null
         else round((y.total_revenue - d.total_revenue) * 100.0 / d.total_revenue, 1) end as "Revenue DoD %",
    case when d.total_orders = 0 then null
         else round((y.total_orders - d.total_orders) * 100.0 / d.total_orders, 1) end as "Orders DoD %",
    case when d.aov = 0 then null
         else round((y.aov - d.aov) * 100.0 / d.aov, 1) end as "AOV DoD %"
FROM yesterday y
CROSS JOIN day_before d
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

#### Question: Hourly Sales (Yesterday vs Day Before)

Compare yesterday's hourly performance with the day before.

**Domain Reference**: [Hourly Sales Trend](../domains/sales.md#6-hourly-sales-trend)

```sql
WITH yesterday_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_yesterday
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
),
day_before_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(gmv) as sales_day_before
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
    GROUP BY 1
)
SELECT
    COALESCE(y.hour_of_day, d.hour_of_day) as hour_of_day,
    COALESCE(y.sales_yesterday, 0) as sales_yesterday,
    COALESCE(d.sales_day_before, 0) as sales_day_before
FROM yesterday_sales y
FULL OUTER JOIN day_before_sales d ON y.hour_of_day = d.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "graph.dimensions": ["hour_of_day"],
  "graph.metrics": ["sales_yesterday", "sales_day_before"],
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

#### Question: Top Channels Yesterday

Revenue breakdown by sales channel.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.gmv) as "Revenue",
    COUNT(distinct o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
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

#### Question: Top Products Yesterday

Best selling products by revenue.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.product_name as "Product",
    SUM(s.revenue) as "Revenue",
    SUM(s.quantity) as "Units Sold"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date - INTERVAL '1 day'
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
WHERE date(p.payment_timestamp) = current_date - INTERVAL '1 day'
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

Customer acquisition breakdown for yesterday.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    CASE
        WHEN date(c.first_order_date) = current_date - INTERVAL '1 day' THEN 'New'
        ELSE 'Returning'
    END as "Customer Type",
    COUNT(distinct o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
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

#### Question: Discount Impact Yesterday

Discount usage and impact on revenue.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    COUNT(distinct order_id) as "Total Orders",
    COUNT(distinct case when total_discount_amount > 0 then order_id end) as "Discounted Orders",
    ROUND(COUNT(distinct case when total_discount_amount > 0 then order_id end) * 100.0
        / NULLIF(COUNT(distinct order_id), 0), 1) as "Discount Rate %",
    SUM(coalesce(total_discount_amount, 0)) as "Total Discounts",
    ROUND(AVG(case when total_discount_amount > 0
        then total_discount_amount * 100.0 / NULLIF(gmv, 0) end), 1) as "Avg Discount %"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
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

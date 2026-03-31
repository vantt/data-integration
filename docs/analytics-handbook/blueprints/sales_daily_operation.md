# Daily Sales Performance Blueprint

**Playbook**: [Daily Sales Operations](../playbooks/sales_daily_operation.md)

This blueprint creates a real-time sales monitoring dashboard for daily operations, organized into tabs for clarity.

## 📂 Collection: Operations > Daily Monitoring

This collection contains operational dashboards updated in real-time.

---

### Dashboard: Daily Sales Dashboard

**Description**: Real-time monitoring of today's sales performance — KPIs, hourly trends, channels, products, customers, and payments across 4 organized tabs.

---

### 📑 Tab: Tổng quan

#### Question: Gross Revenue

**Domain Reference**: [Gross Revenue (GMV)](../domains/sales.md#1-gross-revenue-gmv)

```sql
WITH today AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
),
yesterday AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT
    t.val as "Gross Revenue",
    CASE WHEN y.val = 0 THEN NULL
         ELSE ROUND((t.val - y.val) * 100.0 / y.val, 1) END as "DoD %"
FROM today t CROSS JOIN yesterday y
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 5, "size_y": 3 }
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
WITH today AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
),
yesterday AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT
    t.val as "Net Revenue",
    CASE WHEN y.val = 0 THEN NULL
         ELSE ROUND((t.val - y.val) * 100.0 / y.val, 1) END as "DoD %"
FROM today t CROSS JOIN yesterday y
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 5, "size_x": 5, "size_y": 3 }
```

#### Question: Total Orders

```sql
WITH today AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
),
yesterday AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT
    t.val as "Total Orders",
    CASE WHEN y.val = 0 THEN NULL
         ELSE ROUND((t.val - y.val) * 100.0 / y.val, 1) END as "DoD %"
FROM today t CROSS JOIN yesterday y
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: AOV

```sql
WITH today AS (
    SELECT CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
                ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
),
yesterday AS (
    SELECT CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
                ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT
    ROUND(t.val, 0) as "AOV",
    CASE WHEN y.val = 0 THEN NULL
         ELSE ROUND((t.val - y.val) * 100.0 / y.val, 1) END as "DoD %"
FROM today t CROSS JOIN yesterday y
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 14, "size_x": 4, "size_y": 3 }
```

#### Question: New Customers

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT COUNT(DISTINCT o.customer_key) as "New Customers"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND date(c.first_order_date) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 4, "size_y": 3 }
```

#### Question: Returning Customers

```sql
SELECT COUNT(DISTINCT o.customer_key) as "Returning Customers"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND date(c.first_order_date) < current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 4, "size_x": 4, "size_y": 3 }
```

#### Question: Returns

```sql
SELECT COUNT(DISTINCT order_id) as "Returns"
FROM fact_orders
WHERE date(order_timestamp) = current_date
  AND fulfillment_status = 'RETURNED'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 8, "size_x": 4, "size_y": 3 }
```

#### Question: Discount Rate

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Discount Rate %"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 3, "size_y": 3 }
```

#### Question: Total Discounts

```sql
SELECT COALESCE(SUM(discount_amount), 0) as "Total Discounts"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 15, "size_x": 3, "size_y": 3 }
```

---

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
    COALESCE(c.hour_of_day, p.hour_of_day) as "Hour",
    COALESCE(c.sales_today, 0) as "Today",
    COALESCE(p.sales_yesterday, 0) as "Yesterday"
FROM current_sales c
FULL OUTER JOIN previous_sales p ON c.hour_of_day = p.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "graph.dimensions": ["Hour"],
  "graph.metrics": ["Today", "Yesterday"],
  "graph.colors": ["#509EE3", "#CCCCCC"],
  "graph.x_axis.title_text": "Hour of Day",
  "graph.y_axis.title_text": "Revenue"
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 12, "size_y": 8 }
```

#### Question: Cumulative Revenue

Running total of revenue throughout the day — today vs yesterday.

```sql
WITH hours AS (
    SELECT UNNEST(GENERATE_SERIES(0, 23)) as hour_of_day
),
today_hourly AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as revenue
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
    GROUP BY 1
),
yesterday_hourly AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as revenue
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    h.hour_of_day as "Hour",
    COALESCE(SUM(t.revenue) OVER (ORDER BY h.hour_of_day), 0) as "Today (Cumulative)",
    COALESCE(SUM(y.revenue) OVER (ORDER BY h.hour_of_day), 0) as "Yesterday (Cumulative)"
FROM hours h
LEFT JOIN today_hourly t ON h.hour_of_day = t.hour_of_day
LEFT JOIN yesterday_hourly y ON h.hour_of_day = y.hour_of_day
WHERE h.hour_of_day <= EXTRACT(HOUR FROM NOW()) + 1
   OR EXISTS (SELECT 1 FROM yesterday_hourly yy WHERE yy.hour_of_day = h.hour_of_day)
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "graph.dimensions": ["Hour"],
  "graph.metrics": ["Today (Cumulative)", "Yesterday (Cumulative)"],
  "graph.colors": ["#88BF4D", "#CCCCCC"],
  "graph.x_axis.title_text": "Hour of Day",
  "graph.y_axis.title_text": "Cumulative Revenue"
}
```

```json metabase-pos
{ "row": 6, "col": 12, "size_x": 6, "size_y": 8 }
```

---

### 📑 Tab: Kênh bán hàng

#### Question: Revenue by Channel

Revenue breakdown by sales channel.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "pie.dimension": ["Channel"],
  "pie.metric": "Revenue"
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 9, "size_y": 8 }
```

#### Question: Orders by Channel

Order count breakdown by sales channel.

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "graph.dimensions": ["Channel"],
  "graph.metrics": ["Orders"]
}
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 9, "size_y": 8 }
```

#### Question: Channel Performance vs Yesterday

Channel-level comparison: today vs yesterday with change %.

```sql
WITH today AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(o.net_revenue), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE date(o.order_timestamp) = current_date
    GROUP BY 1
),
yesterday AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(o.net_revenue), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
)
SELECT
    COALESCE(t.channel_name, y.channel_name) as "Channel",
    COALESCE(t.orders, 0) as "Orders Today",
    COALESCE(y.orders, 0) as "Orders Yesterday",
    COALESCE(t.revenue, 0) as "Revenue Today",
    COALESCE(y.revenue, 0) as "Revenue Yesterday",
    CASE WHEN COALESCE(y.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(t.revenue, 0) - y.revenue) * 100.0 / y.revenue, 1) END as "Revenue Change %"
FROM today t
FULL OUTER JOIN yesterday y ON t.channel_name = y.channel_name
ORDER BY COALESCE(t.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Sản phẩm

#### Question: Top 10 Products by Revenue

Best selling products today by revenue.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.product_name as "Product",
    SUM(s.quantity) as "Units Sold",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date
GROUP BY 1
ORDER BY 3 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 12, "size_y": 8 }
```

#### Question: Top 10 Products by Quantity

Products with the highest unit sales today.

```sql
SELECT
    p.product_name as "Product",
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
  "display": "bar",
  "graph.dimensions": ["Product"],
  "graph.metrics": ["Units Sold"]
}
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 6, "size_y": 8 }
```

#### Question: Revenue by Product Type

Revenue breakdown by product category/type.

```sql
SELECT
    COALESCE(p.product_type, 'Unknown') as "Product Type",
    SUM(s.revenue) as "Revenue",
    SUM(s.quantity) as "Units Sold"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "pie.dimension": ["Product Type"],
  "pie.metric": "Revenue"
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 9, "size_y": 8 }
```

#### Question: Product Performance Table

Full product performance detail with quantity, revenue, and average price.

```sql
SELECT
    p.product_name as "Product",
    COALESCE(p.product_type, 'Unknown') as "Type",
    SUM(s.quantity) as "Qty",
    SUM(s.revenue) as "Revenue",
    ROUND(SUM(s.revenue) / NULLIF(SUM(s.quantity), 0), 0) as "Avg Price"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date
GROUP BY 1, 2
ORDER BY 4 DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 8, "col": 9, "size_x": 9, "size_y": 8 }
```

---

### 📑 Tab: Khách hàng & Thanh toán

#### Question: New vs Returning Customers

Customer acquisition breakdown for today.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    CASE
        WHEN date(c.first_order_date) = current_date THEN 'New'
        ELSE 'Returning'
    END as "Customer Type",
    COUNT(DISTINCT o.order_id) as "Orders",
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
{ "row": 0, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Orders by Status

Order status distribution for today.

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(net_revenue), 0) as "Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "pie.dimension": ["Status"],
  "pie.metric": "Orders"
}
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 9, "size_y": 6 }
```

#### Question: Payment Method Distribution

Breakdown of transaction volume by payment method.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "Payment Method",
    COUNT(*) as "Transactions",
    COALESCE(SUM(p.amount), 0) as "Amount"
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
WHERE date(p.payment_timestamp) = current_date
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "pie",
  "pie.dimension": ["Payment Method"],
  "pie.metric": "Transactions"
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Discount Impact

Discount usage and impact on revenue.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    COUNT(DISTINCT order_id) as "Total Orders",
    COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) as "Discounted Orders",
    ROUND(COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1) as "Discount Rate %",
    SUM(COALESCE(discount_amount, 0)) as "Total Discounts",
    ROUND(AVG(CASE WHEN discount_amount > 0
        THEN discount_amount * 100.0 / NULLIF(gross_revenue, 0) END), 1) as "Avg Discount %"
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
{ "row": 6, "col": 9, "size_x": 9, "size_y": 6 }
```

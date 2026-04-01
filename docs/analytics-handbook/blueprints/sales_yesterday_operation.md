# Yesterday's Sales Performance Blueprint

**Playbook**: [Yesterday's Sales Operations](../playbooks/sales_yesterday_operation.md)

This blueprint creates a finalized sales review dashboard for yesterday's operations with day-over-day comparisons, organized into tabs.

## 📂 Collection: Operations > Daily Monitoring

This collection contains operational dashboards. Yesterday's dashboard uses finalized (complete) data.

---

### Dashboard: Yesterday's Sales Dashboard

**Description**: Finalized review of yesterday's sales performance — KPIs with DoD comparisons, hourly trends, channels, products, customers, and payments across 4 tabs.

---

### 📑 Tab: Tổng quan

#### Question: Health Score

Điểm sức khỏe kinh doanh (0-100) dựa trên 4 chỉ số: Revenue Momentum, Order Momentum, Customer Loyalty, AOV Stability. So sánh 7 ngày gần nhất vs 7 ngày trước đó (tính đến hôm qua).

```sql
WITH
recent AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '7 days' AND current_date - INTERVAL '1 day'
),
previous AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '14 days' AND current_date - INTERVAL '8 days'
),
customer_loyalty AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date - INTERVAL '7 days' THEN o.customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
        ) as returning_rate
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '7 days' AND current_date - INTERVAL '1 day'
),
scores AS (
    SELECT
        CASE WHEN p.revenue = 0 THEN 0 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 5 THEN 25 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 0 THEN 20 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -10 THEN 15 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -25 THEN 8 ELSE 0 END as revenue_score,
        CASE WHEN p.orders = 0 THEN 0 WHEN (r.orders-p.orders)*100.0/p.orders >= 5 THEN 25 WHEN (r.orders-p.orders)*100.0/p.orders >= 0 THEN 20 WHEN (r.orders-p.orders)*100.0/p.orders >= -10 THEN 15 WHEN (r.orders-p.orders)*100.0/p.orders >= -25 THEN 8 ELSE 0 END as orders_score,
        CASE WHEN cl.returning_rate >= 50 THEN 25 WHEN cl.returning_rate >= 35 THEN 20 WHEN cl.returning_rate >= 20 THEN 12 ELSE 5 END as loyalty_score,
        CASE WHEN p.aov = 0 THEN 12 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -5 AND 15 THEN 25 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -15 AND -5 THEN 15 WHEN (r.aov-p.aov)*100.0/p.aov > 15 THEN 20 ELSE 5 END as aov_score
    FROM recent r, previous p, customer_loyalty cl
)
SELECT revenue_score + orders_score + loyalty_score + aov_score as "Health Score"
FROM scores
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 4, "size_y": 4 }
```

#### Question: Health Breakdown

Chi tiết từng thành phần của Health Score.

```sql
WITH
recent AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '7 days' AND current_date - INTERVAL '1 day'
),
previous AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '14 days' AND current_date - INTERVAL '8 days'
),
customer_loyalty AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date - INTERVAL '7 days' THEN o.customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
        ) as returning_rate
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '7 days' AND current_date - INTERVAL '1 day'
),
raw_scores AS (
    SELECT
        CASE WHEN p.revenue = 0 THEN NULL ELSE ROUND((r.revenue - p.revenue) * 100.0 / p.revenue, 1) END as rev_wow,
        CASE WHEN p.orders = 0 THEN NULL ELSE ROUND((r.orders - p.orders) * 100.0 / p.orders, 1) END as ord_wow,
        cl.returning_rate,
        CASE WHEN p.aov = 0 THEN NULL ELSE ROUND((r.aov - p.aov) * 100.0 / p.aov, 1) END as aov_wow,
        CASE WHEN p.revenue = 0 THEN 0 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 5 THEN 25 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= 0 THEN 20 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -10 THEN 15 WHEN (r.revenue-p.revenue)*100.0/p.revenue >= -25 THEN 8 ELSE 0 END as rev_sc,
        CASE WHEN p.orders = 0 THEN 0 WHEN (r.orders-p.orders)*100.0/p.orders >= 5 THEN 25 WHEN (r.orders-p.orders)*100.0/p.orders >= 0 THEN 20 WHEN (r.orders-p.orders)*100.0/p.orders >= -10 THEN 15 WHEN (r.orders-p.orders)*100.0/p.orders >= -25 THEN 8 ELSE 0 END as ord_sc,
        CASE WHEN cl.returning_rate >= 50 THEN 25 WHEN cl.returning_rate >= 35 THEN 20 WHEN cl.returning_rate >= 20 THEN 12 ELSE 5 END as loy_sc,
        CASE WHEN p.aov = 0 THEN 12 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -5 AND 15 THEN 25 WHEN (r.aov-p.aov)*100.0/p.aov BETWEEN -15 AND -5 THEN 15 WHEN (r.aov-p.aov)*100.0/p.aov > 15 THEN 20 ELSE 5 END as aov_sc
    FROM recent r, previous p, customer_loyalty cl
)
SELECT * FROM (
    SELECT 1 as sort, 'Doanh thu (WoW)' as "Component", rev_wow as "Change %",
        CASE WHEN rev_sc >= 20 THEN 'OK' WHEN rev_sc >= 15 THEN 'Chú ý' ELSE 'Báo động' END as "Status"
    FROM raw_scores
    UNION ALL
    SELECT 2, 'Đơn hàng (WoW)', ord_wow,
        CASE WHEN ord_sc >= 20 THEN 'OK' WHEN ord_sc >= 15 THEN 'Chú ý' ELSE 'Báo động' END
    FROM raw_scores
    UNION ALL
    SELECT 3, 'Khách quay lại', returning_rate,
        CASE WHEN loy_sc >= 20 THEN 'OK' WHEN loy_sc >= 12 THEN 'Chú ý' ELSE 'Báo động' END
    FROM raw_scores
    UNION ALL
    SELECT 4, 'AOV ổn định', aov_wow,
        CASE WHEN aov_sc >= 20 THEN 'OK' WHEN aov_sc >= 15 THEN 'Chú ý' ELSE 'Báo động' END
    FROM raw_scores
) t ORDER BY sort
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 0, "col": 4, "size_x": 14, "size_y": 4 }
```

---

#### Question: Yesterday Date Label

```sql
SELECT strftime(current_date - INTERVAL '1 day', '%A, %Y-%m-%d') as "Date Reviewed"
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 2 }
```

#### Question: Gross Revenue

**Domain Reference**: [Gross Revenue (GMV)](../domains/sales.md#1-gross-revenue-gmv)

```sql
SELECT COALESCE(SUM(gross_revenue), 0) as "Gross Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 4, "size_y": 3 }
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
SELECT COALESCE(SUM(net_revenue), 0) as "Net Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 6, "col": 4, "size_x": 4, "size_y": 3 }
```

#### Question: Total Collected

**Domain Reference**: [Total Collected](../domains/sales.md#2b-total-collected)

```sql
SELECT COALESCE(SUM(total_collected), 0) as "Total Collected"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 6, "col": 8, "size_x": 4, "size_y": 3 }
```

#### Question: Total Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 6, "col": 12, "size_x": 3, "size_y": 3 }
```

#### Question: AOV

```sql
SELECT CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
            ELSE ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 0) END as "AOV"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 6, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### Question: New Customers

```sql
SELECT COUNT(DISTINCT o.customer_key) as "New Customers"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
  AND date(c.first_order_date) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 3, "size_y": 3 }
```

#### Question: Returning Customers

```sql
SELECT COUNT(DISTINCT o.customer_key) as "Returning Customers"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
  AND date(c.first_order_date) < current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 9, "col": 3, "size_x": 3, "size_y": 3 }
```

#### Question: Returns

```sql
SELECT COUNT(DISTINCT order_id) as "Returns"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
  AND fulfillment_status = 'RETURNED'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 9, "col": 6, "size_x": 3, "size_y": 3 }
```

#### Question: Items per Order

```sql
SELECT ROUND(
    SUM(s.quantity)::FLOAT / NULLIF(COUNT(DISTINCT s.order_id), 0), 1
) as "Items/Order"
FROM fact_sales s
WHERE date(s.sol_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 9, "col": 9, "size_x": 3, "size_y": 3 }
```

#### Question: Discount Rate

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Discount Rate %"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 9, "col": 12, "size_x": 3, "size_y": 3 }
```

#### Question: Total Discounts

```sql
SELECT COALESCE(SUM(discount_amount), 0) as "Total Discounts"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 9, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### Question: DoD Comparison

Day-over-day comparison: yesterday vs day before.

```sql
WITH yesterday AS (
    SELECT
        COALESCE(SUM(gross_revenue), 0) as gross_revenue,
        COALESCE(SUM(net_revenue), 0) as net_revenue,
        COUNT(DISTINCT order_id) as total_orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 0) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
),
day_before AS (
    SELECT
        COALESCE(SUM(gross_revenue), 0) as gross_revenue,
        COALESCE(SUM(net_revenue), 0) as net_revenue,
        COUNT(DISTINCT order_id) as total_orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 0) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
)
SELECT * FROM (
    SELECT 1 as sort, 'Gross Revenue' as "Metric", y.gross_revenue as "Yesterday", d.gross_revenue as "Day Before",
        CASE WHEN d.gross_revenue = 0 THEN NULL ELSE ROUND((y.gross_revenue - d.gross_revenue) * 100.0 / d.gross_revenue, 1) END as "Change %"
    FROM yesterday y, day_before d
    UNION ALL
    SELECT 2, 'Net Revenue', y.net_revenue, d.net_revenue,
        CASE WHEN d.net_revenue = 0 THEN NULL ELSE ROUND((y.net_revenue - d.net_revenue) * 100.0 / d.net_revenue, 1) END
    FROM yesterday y, day_before d
    UNION ALL
    SELECT 3, 'Orders', y.total_orders, d.total_orders,
        CASE WHEN d.total_orders = 0 THEN NULL ELSE ROUND((y.total_orders - d.total_orders) * 100.0 / d.total_orders, 1) END
    FROM yesterday y, day_before d
    UNION ALL
    SELECT 4, 'AOV', y.aov, d.aov,
        CASE WHEN d.aov = 0 THEN NULL ELSE ROUND((y.aov - d.aov) * 100.0 / d.aov, 1) END
    FROM yesterday y, day_before d
) t ORDER BY sort
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 3 }
```

---

#### Question: Hourly Sales Trend

Compare yesterday's hourly performance with the day before.

**Domain Reference**: [Hourly Sales Trend](../domains/sales.md#6-hourly-sales-trend)

```sql
WITH yesterday_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as sales_yesterday
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
),
day_before_sales AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as sales_day_before
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
    GROUP BY 1
)
SELECT
    COALESCE(y.hour_of_day, d.hour_of_day) as "Hour",
    COALESCE(y.sales_yesterday, 0) as "Yesterday",
    COALESCE(d.sales_day_before, 0) as "Day Before"
FROM yesterday_sales y
FULL OUTER JOIN day_before_sales d ON y.hour_of_day = d.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "graph.dimensions": ["Hour"],
  "graph.metrics": ["Yesterday", "Day Before"],
  "graph.colors": ["#509EE3", "#CCCCCC"],
  "graph.x_axis.title_text": "Hour of Day",
  "graph.y_axis.title_text": "Revenue"
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 12, "size_y": 8 }
```

#### Question: Cumulative Revenue

Running total comparison — yesterday vs day before.

```sql
WITH hours AS (
    SELECT UNNEST(GENERATE_SERIES(0, 23)) as hour_of_day
),
yesterday_hourly AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as revenue
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
),
day_before_hourly AS (
    SELECT
        EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
        SUM(net_revenue) as revenue
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
    GROUP BY 1
)
SELECT
    h.hour_of_day as "Hour",
    COALESCE(SUM(y.revenue) OVER (ORDER BY h.hour_of_day), 0) as "Yesterday (Cumulative)",
    COALESCE(SUM(d.revenue) OVER (ORDER BY h.hour_of_day), 0) as "Day Before (Cumulative)"
FROM hours h
LEFT JOIN yesterday_hourly y ON h.hour_of_day = y.hour_of_day
LEFT JOIN day_before_hourly d ON h.hour_of_day = d.hour_of_day
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "graph.dimensions": ["Hour"],
  "graph.metrics": ["Yesterday (Cumulative)", "Day Before (Cumulative)"],
  "graph.colors": ["#88BF4D", "#CCCCCC"],
  "graph.x_axis.title_text": "Hour of Day",
  "graph.y_axis.title_text": "Cumulative Revenue"
}
```

```json metabase-pos
{ "row": 15, "col": 12, "size_x": 6, "size_y": 8 }
```

---

### 📑 Tab: Kênh bán hàng

#### Question: Revenue by Channel

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
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

#### Question: Revenue by Channel Category

Online vs Offline vs Internal breakdown.

```sql
SELECT
    c.channel_category as "Category",
    SUM(o.net_revenue) as "Revenue",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "graph.dimensions": ["Category"],
  "graph.metrics": ["Revenue", "Orders"]
}
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 9, "size_y": 8 }
```

#### Question: Channel Performance vs Day Before

```sql
WITH yesterday AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(o.net_revenue), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
    GROUP BY 1
),
day_before AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(o.net_revenue), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE date(o.order_timestamp) = current_date - INTERVAL '2 days'
    GROUP BY 1
)
SELECT
    COALESCE(y.channel_name, d.channel_name) as "Channel",
    COALESCE(y.orders, 0) as "Orders Yesterday",
    COALESCE(d.orders, 0) as "Orders Day Before",
    COALESCE(y.revenue, 0) as "Revenue Yesterday",
    COALESCE(d.revenue, 0) as "Revenue Day Before",
    CASE WHEN COALESCE(d.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(y.revenue, 0) - d.revenue) * 100.0 / d.revenue, 1) END as "Revenue Change %"
FROM yesterday y
FULL OUTER JOIN day_before d ON y.channel_name = d.channel_name
ORDER BY COALESCE(y.revenue, 0) DESC
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

#### Question: Sales by Branch

```sql
SELECT
    bl.branch_location_name as "Branch",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Sản phẩm

#### Question: Top 10 Products by Revenue

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.product_name as "Product",
    SUM(s.quantity) as "Units Sold",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date - INTERVAL '1 day'
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

```sql
SELECT
    p.product_name as "Product",
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
  "display": "bar",
  "graph.dimensions": ["Product"],
  "graph.metrics": ["Units Sold"]
}
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 6, "size_y": 8 }
```

#### Question: Revenue by Product Type

```sql
SELECT
    COALESCE(p.product_type, 'Unknown') as "Product Type",
    SUM(s.revenue) as "Revenue",
    SUM(s.quantity) as "Units Sold"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date - INTERVAL '1 day'
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

```sql
SELECT
    p.product_name as "Product",
    COALESCE(p.product_type, 'Unknown') as "Type",
    SUM(s.quantity) as "Qty",
    SUM(s.revenue) as "Revenue",
    ROUND(SUM(s.revenue) / NULLIF(SUM(s.quantity), 0), 0) as "Avg Price"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) = current_date - INTERVAL '1 day'
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

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    CASE
        WHEN date(c.first_order_date) = current_date - INTERVAL '1 day' THEN 'New'
        ELSE 'Returning'
    END as "Customer Type",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.net_revenue) as "Revenue"
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
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Revenue by Customer Segment

Breakdown by RFM-based customer segments: VIP, Loyal, Regular.

```sql
SELECT
    COALESCE(c.customer_segment, 'Unknown') as "Segment",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.net_revenue) as "Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "bar",
  "graph.dimensions": ["Segment"],
  "graph.metrics": ["Revenue", "Orders"]
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

#### Question: Returning Customer Rate

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date - INTERVAL '1 day' THEN o.customer_key END) * 100.0
        / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
    ) as "Returning Rate %"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 4, "size_y": 3 }
```

#### Question: At Risk Customers

```sql
SELECT COUNT(*) as "At Risk Customers"
FROM dim_customers
WHERE customer_status = 'At Risk'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 13, "size_x": 5, "size_y": 3 }
```

#### Question: Orders by Status

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(net_revenue), 0) as "Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
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
{ "row": 9, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Payment Method Distribution

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "Payment Method",
    COUNT(*) as "Transactions",
    COALESCE(SUM(p.amount), 0) as "Amount"
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
WHERE date(p.payment_timestamp) = current_date - INTERVAL '1 day'
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
{ "row": 9, "col": 9, "size_x": 9, "size_y": 6 }
```

#### Question: Discount Impact

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
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 4 }
```

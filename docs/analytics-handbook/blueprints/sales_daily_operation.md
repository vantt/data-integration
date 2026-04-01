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

#### Question: Health Score

Điểm sức khỏe kinh doanh (0-100) dựa trên 4 chỉ số: Revenue Momentum, Order Momentum, Customer Loyalty, AOV Stability. So sánh 7 ngày gần nhất vs 7 ngày trước đó.

```sql
WITH
recent AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
),
previous AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '13 days' AND current_date - INTERVAL '7 days'
),
customer_loyalty AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date - INTERVAL '6 days' THEN o.customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
        ) as returning_rate
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
),
scores AS (
    SELECT
        CASE
            WHEN p.revenue = 0 THEN 0
            WHEN (r.revenue - p.revenue) * 100.0 / p.revenue >= 5 THEN 25
            WHEN (r.revenue - p.revenue) * 100.0 / p.revenue >= 0 THEN 20
            WHEN (r.revenue - p.revenue) * 100.0 / p.revenue >= -10 THEN 15
            WHEN (r.revenue - p.revenue) * 100.0 / p.revenue >= -25 THEN 8
            ELSE 0
        END as revenue_score,
        CASE
            WHEN p.orders = 0 THEN 0
            WHEN (r.orders - p.orders) * 100.0 / p.orders >= 5 THEN 25
            WHEN (r.orders - p.orders) * 100.0 / p.orders >= 0 THEN 20
            WHEN (r.orders - p.orders) * 100.0 / p.orders >= -10 THEN 15
            WHEN (r.orders - p.orders) * 100.0 / p.orders >= -25 THEN 8
            ELSE 0
        END as orders_score,
        CASE
            WHEN cl.returning_rate >= 50 THEN 25
            WHEN cl.returning_rate >= 35 THEN 20
            WHEN cl.returning_rate >= 20 THEN 12
            ELSE 5
        END as loyalty_score,
        CASE
            WHEN p.aov = 0 THEN 12
            WHEN (r.aov - p.aov) * 100.0 / p.aov BETWEEN -5 AND 15 THEN 25
            WHEN (r.aov - p.aov) * 100.0 / p.aov BETWEEN -15 AND -5 THEN 15
            WHEN (r.aov - p.aov) * 100.0 / p.aov > 15 THEN 20
            ELSE 5
        END as aov_score
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

Chi tiết từng thành phần của Health Score: điểm, WoW%, và trạng thái.

```sql
WITH
recent AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
),
previous AS (
    SELECT
        COALESCE(SUM(net_revenue), 0) as revenue,
        COUNT(DISTINCT order_id) as orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) BETWEEN current_date - INTERVAL '13 days' AND current_date - INTERVAL '7 days'
),
customer_loyalty AS (
    SELECT
        ROUND(
            COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date - INTERVAL '6 days' THEN o.customer_key END) * 100.0
            / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
        ) as returning_rate
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE date(o.order_timestamp) BETWEEN current_date - INTERVAL '6 days' AND current_date
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

#### Question: Gross Revenue

**Domain Reference**: [Gross Revenue (GMV)](../domains/sales.md#1-gross-revenue-gmv)

```sql
SELECT COALESCE(SUM(gross_revenue), 0) as "Gross Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 4, "size_y": 3 }
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
SELECT COALESCE(SUM(net_revenue), 0) as "Net Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 4, "size_x": 4, "size_y": 3 }
```

#### Question: Total Collected

**Domain Reference**: [Total Collected](../domains/sales.md#2b-total-collected)

```sql
SELECT COALESCE(SUM(total_collected), 0) as "Total Collected"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 8, "size_x": 4, "size_y": 3 }
```

#### Question: Total Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 12, "size_x": 3, "size_y": 3 }
```

#### Question: AOV

```sql
SELECT CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
            ELSE ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 0) END as "AOV"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### Question: New Customers

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
{ "row": 7, "col": 0, "size_x": 3, "size_y": 3 }
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
{ "row": 7, "col": 3, "size_x": 3, "size_y": 3 }
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
{ "row": 7, "col": 6, "size_x": 3, "size_y": 3 }
```

#### Question: Items per Order

```sql
SELECT ROUND(
    SUM(s.quantity)::FLOAT / NULLIF(COUNT(DISTINCT s.order_id), 0), 1
) as "Items/Order"
FROM fact_sales s
WHERE date(s.sol_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 7, "col": 9, "size_x": 3, "size_y": 3 }
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
{ "row": 7, "col": 12, "size_x": 3, "size_y": 3 }
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
{ "row": 7, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### Question: DoD Comparison

Day-over-day comparison of key metrics: today vs yesterday.

```sql
WITH today AS (
    SELECT
        COALESCE(SUM(gross_revenue), 0) as gross_revenue,
        COALESCE(SUM(net_revenue), 0) as net_revenue,
        COUNT(DISTINCT order_id) as total_orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 0) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
),
yesterday AS (
    SELECT
        COALESCE(SUM(gross_revenue), 0) as gross_revenue,
        COALESCE(SUM(net_revenue), 0) as net_revenue,
        COUNT(DISTINCT order_id) as total_orders,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 0) END as aov
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT * FROM (
    SELECT 1 as sort, 'Gross Revenue' as "Metric", t.gross_revenue as "Today", y.gross_revenue as "Yesterday",
        CASE WHEN y.gross_revenue = 0 THEN NULL ELSE ROUND((t.gross_revenue - y.gross_revenue) * 100.0 / y.gross_revenue, 1) END as "Change %"
    FROM today t, yesterday y
    UNION ALL
    SELECT 2, 'Net Revenue', t.net_revenue, y.net_revenue,
        CASE WHEN y.net_revenue = 0 THEN NULL ELSE ROUND((t.net_revenue - y.net_revenue) * 100.0 / y.net_revenue, 1) END
    FROM today t, yesterday y
    UNION ALL
    SELECT 3, 'Orders', t.total_orders, y.total_orders,
        CASE WHEN y.total_orders = 0 THEN NULL ELSE ROUND((t.total_orders - y.total_orders) * 100.0 / y.total_orders, 1) END
    FROM today t, yesterday y
    UNION ALL
    SELECT 4, 'AOV', t.aov, y.aov,
        CASE WHEN y.aov = 0 THEN NULL ELSE ROUND((t.aov - y.aov) * 100.0 / y.aov, 1) END
    FROM today t, yesterday y
) t ORDER BY sort
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 3 }
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
{ "row": 13, "col": 0, "size_x": 12, "size_y": 8 }
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
{ "row": 13, "col": 12, "size_x": 6, "size_y": 8 }
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

#### Question: Revenue by Channel Category

Online vs Offline vs Internal breakdown.

```sql
SELECT
    c.channel_category as "Category",
    SUM(o.net_revenue) as "Revenue",
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
  "graph.dimensions": ["Category"],
  "graph.metrics": ["Revenue", "Orders"]
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

#### Question: Sales by Branch

Revenue and order count by store/branch location.

```sql
SELECT
    bl.branch_location_name as "Branch",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE date(o.order_timestamp) = current_date
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
WHERE date(o.order_timestamp) = current_date
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

Tỷ lệ đơn hàng từ khách quay lại — nếu giảm dần, đây là red flag lớn nhất.

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN date(c.first_order_date) < current_date THEN o.customer_key END) * 100.0
        / NULLIF(COUNT(DISTINCT o.customer_key), 0), 1
    ) as "Returning Rate %"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 4, "size_y": 3 }
```

#### Question: At Risk Customers

Khách hàng có nguy cơ mất — đã mua trước đây nhưng không quay lại gần đây.

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
WHERE date(order_timestamp) = current_date
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

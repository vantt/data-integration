# 📘 Blueprint: Marketing Weekly Tracker

**Playbook**: [Marketing Weekly Tracker](../playbooks/marketing_weekly_tracker.md)

> **Target Collection:** `Marketing` > `Weekly Reports`
> **Role:** Marketing Manager, Brand Manager
> **Archetype:** Operational Cockpit

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Marketing Weekly Tracker

**Description**: Weekly channel performance, customer acquisition, promotions, and social commerce monitoring.

---

#### ❓ Question: Weekly Revenue

**Domain Reference**: [Revenue](../domains/sales.md#1-gmv-gross-merchandise-value)

```sql
SELECT COALESCE(SUM(net_revenue), 0) as "Weekly Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Weekly Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: Ecommerce Revenue

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT COALESCE(SUM(o.net_revenue), 0) as "Ecommerce Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_category = 'Ecommerce'
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Ecommerce Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 5, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: Offline Revenue

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT COALESCE(SUM(o.net_revenue), 0) as "Offline Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_category = 'Offline'
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Offline Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: New Customers This Week

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT COUNT(DISTINCT customer_key) as "New Customers"
FROM dim_customers
WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(first_order_date) < date_trunc('week', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Revenue by Platform

Revenue broken down by platform (Shopee, Lazada, TikTok, Facebook, POS, Web, etc.).

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.platform as "Platform",
    SUM(o.net_revenue) as "Revenue",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Platform"],
    "graph.metrics": ["Revenue"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 8 }
```

#### ❓ Question: Channel Performance Table

Detailed channel breakdown with WoW comparison.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
WITH this_week AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        SUM(o.net_revenue) as revenue,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_name,
        COUNT(DISTINCT o.order_id) as orders,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
    GROUP BY 1
)
SELECT
    tw.channel_name as "Channel",
    tw.orders as "Orders",
    tw.revenue as "Revenue",
    tw.aov as "AOV",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tw.revenue - COALESCE(lw.revenue, 0)) * 100.0 / lw.revenue, 1) END as "WoW Revenue %",
    CASE WHEN COALESCE(lw.orders, 0) = 0 THEN NULL
         ELSE ROUND((tw.orders - COALESCE(lw.orders, 0)) * 100.0 / lw.orders, 1) END as "WoW Orders %"
FROM this_week tw
LEFT JOIN last_week lw ON tw.channel_name = lw.channel_name
ORDER BY tw.revenue DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND" },
      "AOV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 8 }
```

---

#### ❓ Question: Ecommerce vs Offline Trend (14 Days)

Daily revenue, 2 lines: Ecommerce vs Offline.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    date(o.order_timestamp) as order_date,
    SUM(CASE WHEN c.channel_category = 'Ecommerce' THEN o.net_revenue ELSE 0 END) as "Ecommerce",
    SUM(CASE WHEN c.channel_category = 'Offline' THEN o.net_revenue ELSE 0 END) as "Offline"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= current_date - INTERVAL '14 days'
  AND o.order_timestamp < current_date
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["order_date"],
    "graph.metrics": ["Ecommerce", "Offline"],
    "graph.colors": ["#509EE3", "#F9A825"]
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 12, "size_y": 8 }
```

#### ❓ Question: Revenue by Channel Brand

Revenue by channel brand (JPC, Fine Japan, The Healthy Us, etc.).

```sql
SELECT
    c.channel_brand as "Brand",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_brand IS NOT NULL
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Brand",
    "pie.metric": "Revenue",
    "pie.show_legend": true
  }
}
```

```json metabase-pos
{ "row": 11, "col": 12, "size_x": 6, "size_y": 8 }
```

---

#### ❓ Question: New Customer Acquisition Trend (14 Days)

Daily new customer count over the last 14 days.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    date(first_order_date) as acquisition_date,
    COUNT(DISTINCT customer_key) as "New Customers"
FROM dim_customers
WHERE date(first_order_date) >= current_date - INTERVAL '14 days'
  AND date(first_order_date) < current_date
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["acquisition_date"],
    "graph.metrics": ["New Customers"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New Customers by Channel

Which channels bring in the most new customers this week?

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.customer_key) as "New Customers"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND date(cust.first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(cust.first_order_date) < date_trunc('week', current_date)
  AND date(cust.first_order_date) = date(o.order_timestamp)
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["New Customers"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 19, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Discount Rate This Week

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as "Discount Rate %"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Discount Rate %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Discounted vs Non-Discounted Orders

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    CASE WHEN discount_amount > 0 THEN 'Discounted' ELSE 'Full Price' END as "Type",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
GROUP BY 1
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Type",
    "pie.metric": "Orders",
    "pie.colors": { "Full Price": "#509EE3", "Discounted": "#F9A825" }
  }
}
```

```json metabase-pos
{ "row": 25, "col": 4, "size_x": 5, "size_y": 6 }
```

#### ❓ Question: Promotion Leaderboard

Top 5 active promotions this week.

**Domain Reference**: [Promotion Performance](../domains/sales.md#14-promotion-performance)

```sql
SELECT
    COALESCE(p.promotion_code, 'Unknown') as "Promo Code",
    COUNT(DISTINCT o.order_id) as "Usage Count",
    SUM(o.net_revenue) as "Revenue",
    ROUND(AVG(COALESCE(o.discount_amount, 0) * 100.0 / NULLIF(o.gross_revenue, 0)), 1) as "Avg Discount %"
FROM fact_orders o
JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND p.promotion_code IS NOT NULL
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 3 DESC
LIMIT 5
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 25, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Social Revenue (Facebook + Zalo)

Revenue from social commerce channels this week.

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume)

```sql
SELECT COALESCE(SUM(o.net_revenue), 0) as "Social Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Social Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 31, "col": 0, "size_x": 9, "size_y": 3 }
```

#### ❓ Question: Social Orders

```sql
SELECT COUNT(DISTINCT o.order_id) as "Social Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 31, "col": 9, "size_x": 9, "size_y": 3 }
```

#### ❓ Question: Top 10 Products This Week

Best selling products with channel information.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.product_name as "Product",
    p.brand_name as "Brand",
    SUM(s.quantity) as "Units",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(s.sol_timestamp) < date_trunc('week', current_date)
GROUP BY 1, 2
ORDER BY 4 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [{
      "columns": ["Revenue"],
      "type": "currency",
      "currency": "VND"
    }]
  }
}
```

```json metabase-pos
{ "row": 34, "col": 0, "size_x": 18, "size_y": 6 }
```

# 📘 Blueprint: Marketing Monthly Analysis

**Playbook**: [Marketing Monthly Analysis](../playbooks/marketing_monthly_analysis.md)

> **Target Collection:** `Marketing` > `Monthly Reports`
> **Role:** Marketing Manager, CMO
> **Archetype:** Exploratory Tool + Executive Pulse

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Marketing Monthly Analysis

**Description**: Monthly deep dive — channel strategy, customer acquisition, cohort retention, campaign ROI, and product-brand performance.

---

#### ❓ Question: Monthly Revenue

**Domain Reference**: [GMV](../domains/sales.md#1-gmv-gross-merchandise-value)

```sql
SELECT COALESCE(SUM(gmv), 0) as "Monthly Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Monthly Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Monthly Total Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 4, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Monthly New Customers

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT COUNT(DISTINCT customer_key) as "New Customers"
FROM dim_customers
WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(first_order_date) < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 8, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Monthly Discount Rate

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT ROUND(SUM(COALESCE(total_discount_amount, 0)) * 100.0 / NULLIF(SUM(gmv), 0), 1) as "Discount Rate %"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
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
{ "row": 0, "col": 12, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Channel Mix Trend (6 Months)

Monthly revenue stacked by channel category over 6 months.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as month,
    c.channel_category,
    SUM(o.gmv) as revenue
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["revenue"],
    "stackable.stack_type": "stacked"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 12, "size_y": 8 }
```

#### ❓ Question: Platform Performance Matrix

Full platform breakdown with MoM comparison.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
WITH this_month AS (
    SELECT
        c.platform,
        SUM(o.gmv) as revenue,
        COUNT(DISTINCT o.order_id) as orders,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.gmv) / COUNT(DISTINCT o.order_id) END as aov,
        COUNT(DISTINCT CASE WHEN date(cust.first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
                             AND date(cust.first_order_date) < date_trunc('month', current_date)
                        THEN o.customer_key END) as new_customers
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    LEFT JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT
        c.platform,
        SUM(o.gmv) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    tm.platform as "Platform",
    tm.revenue as "Revenue",
    tm.orders as "Orders",
    tm.aov as "AOV",
    tm.new_customers as "New Customers",
    CASE WHEN COALESCE(lm.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tm.revenue - COALESCE(lm.revenue, 0)) * 100.0 / lm.revenue, 1) END as "MoM Revenue %",
    CASE WHEN COALESCE(lm.orders, 0) = 0 THEN NULL
         ELSE ROUND((tm.orders - COALESCE(lm.orders, 0)) * 100.0 / lm.orders, 1) END as "MoM Orders %"
FROM this_month tm
LEFT JOIN last_month lm ON tm.platform = lm.platform
ORDER BY tm.revenue DESC
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
{ "row": 3, "col": 12, "size_x": 6, "size_y": 8 }
```

---

#### ❓ Question: New Customer Acquisition Trend (6M)

Monthly new customer count over 6 months.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    date_trunc('month', first_order_date)::date as month,
    COUNT(DISTINCT customer_key) as "New Customers"
FROM dim_customers
WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND date(first_order_date) < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["New Customers"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: New Customers by Channel (Monthly)

Which channels acquired the most new customers in the closed month?

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.customer_key) as "New Customers"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND date(cust.first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(cust.first_order_date) < date_trunc('month', current_date)
  AND date(cust.first_order_date) = date(o.order_timestamp)
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
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
{ "row": 11, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Customer Segment Movement

Customer segments with MoM comparison.

**Domain Reference**: [RFM Segment](../domains/customer.md#7-rfm-segment)

```sql
SELECT
    customer_segment as "Segment",
    customer_status as "Status",
    COUNT(*) as "Customer Count",
    SUM(lifetime_value) as "Total LTV"
FROM dim_customers
WHERE customer_id IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Total LTV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Cohort Retention Heatmap

Month-over-month retention by acquisition cohort (last 12 months).

**Domain Reference**: [Retention Rate](../domains/customer.md#5-retention-rate)

```sql
WITH cohort_sizes AS (
    SELECT
        date_trunc('month', first_order_date) as cohort_month,
        COUNT(DISTINCT customer_id) as original_size
    FROM dim_customers
    WHERE first_order_date >= (current_date - INTERVAL '12' MONTH)
    GROUP BY 1
),
retention_activity AS (
    SELECT
        date_trunc('month', c.first_order_date) as cohort_month,
        date_diff('month', c.first_order_date, o.order_timestamp) as month_number,
        COUNT(DISTINCT c.customer_id) as active_customers
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
    WHERE c.first_order_date >= (current_date - INTERVAL '12' MONTH)
      AND o.order_timestamp >= c.first_order_date
      AND o.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1, 2
)
SELECT
    strftime(r.cohort_month, '%Y-%m') as "Cohort",
    r.month_number as "Month #",
    s.original_size as "Cohort Size",
    r.active_customers as "Active",
    ROUND(CAST(r.active_customers AS FLOAT) / s.original_size * 100, 1) as "Retention %"
FROM retention_activity r
JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
WHERE r.month_number <= 6
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": true,
    "table.cell_column": "Retention %",
    "table.columns": [
      { "name": "Cohort", "enabled": true },
      { "name": "Month #", "enabled": true },
      { "name": "Retention %", "enabled": true }
    ]
  }
}
```

```json metabase-pos
{ "row": 17, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Promotion Leaderboard (Monthly)

Top promotions ranked by revenue for the closed month.

**Domain Reference**: [Promotion Performance](../domains/sales.md#14-promotion-performance)

```sql
WITH promo_orders AS (
    SELECT
        COALESCE(p.promotion_code, 'Unknown') as promo_code,
        COUNT(DISTINCT o.order_id) as usage_count,
        SUM(o.gmv) as revenue,
        ROUND(AVG(COALESCE(o.total_discount_amount, 0) * 100.0 / NULLIF(o.gmv, 0)), 1) as avg_discount_pct,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.gmv) / COUNT(DISTINCT o.order_id) END as promo_aov
    FROM fact_orders o
    JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND p.promotion_code IS NOT NULL
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
baseline AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(gmv) / COUNT(DISTINCT order_id) END as non_promo_aov
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND promotion_key IS NULL
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
)
SELECT
    po.promo_code as "Promo Code",
    po.usage_count as "Usage Count",
    po.revenue as "Revenue",
    po.avg_discount_pct as "Avg Discount %",
    po.promo_aov as "Promo AOV",
    b.non_promo_aov as "Non-Promo AOV"
FROM promo_orders po
CROSS JOIN baseline b
ORDER BY po.revenue DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND" },
      "Promo AOV": { "number_style": "currency", "currency": "VND" },
      "Non-Promo AOV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Discount Trend (6M)

Monthly discount rate over 6 months.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    date_trunc('month', order_timestamp)::date as month,
    ROUND(SUM(COALESCE(total_discount_amount, 0)) * 100.0 / NULLIF(SUM(gmv), 0), 1) as "Discount Rate %"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Discount Rate %"],
    "graph.colors": ["#F9A825"],
    "graph.goal_value": 15,
    "graph.show_goal": true,
    "graph.goal_label": "Target < 15%"
  }
}
```

```json metabase-pos
{ "row": 29, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Revenue — Discounted vs Full-Price (6M)

Monthly split of discounted vs full-price revenue.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    date_trunc('month', order_timestamp)::date as month,
    SUM(CASE WHEN total_discount_amount > 0 THEN gmv ELSE 0 END) as "Discounted Revenue",
    SUM(CASE WHEN COALESCE(total_discount_amount, 0) = 0 THEN gmv ELSE 0 END) as "Full-Price Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Discounted Revenue", "Full-Price Revenue"],
    "stackable.stack_type": "stacked",
    "series_settings": {
      "Discounted Revenue": { "color": "#F9A825" },
      "Full-Price Revenue": { "color": "#509EE3" }
    }
  }
}
```

```json metabase-pos
{ "row": 29, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Top 15 Products by Revenue (Monthly)

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.product_name as "Product",
    p.brand_name as "Brand",
    SUM(s.quantity) as "Units",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE date(s.sol_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(s.sol_timestamp) < date_trunc('month', current_date)
GROUP BY 1, 2
ORDER BY 4 DESC
LIMIT 15
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
{ "row": 35, "col": 0, "size_x": 9, "size_y": 8 }
```

#### ❓ Question: Brand Performance Summary

Revenue by product brand for the closed month.

```sql
WITH this_month AS (
    SELECT
        p.brand_name,
        SUM(s.revenue) as revenue,
        SUM(s.quantity) as units,
        COUNT(DISTINCT s.order_id) as order_count
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE date(s.sol_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(s.sol_timestamp) < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT
        p.brand_name,
        SUM(s.revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE date(s.sol_timestamp) >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND date(s.sol_timestamp) < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    COALESCE(tm.brand_name, 'Unknown') as "Brand",
    tm.revenue as "Revenue",
    tm.units as "Units",
    tm.order_count as "Orders",
    CASE WHEN tm.order_count = 0 THEN 0
         ELSE tm.revenue / tm.order_count END as "AOV",
    CASE WHEN COALESCE(lm.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tm.revenue - COALESCE(lm.revenue, 0)) * 100.0 / lm.revenue, 1) END as "MoM %"
FROM this_month tm
LEFT JOIN last_month lm ON tm.brand_name = lm.brand_name
ORDER BY tm.revenue DESC
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
{ "row": 35, "col": 9, "size_x": 9, "size_y": 8 }
```

---

#### ❓ Question: Order Heatmap by Day x Hour

Peak ordering windows for marketing scheduling.

**Domain Reference**: [Hourly Heatmap](../domains/sales.md#7-hourly-heatmap-day-of-week-analysis)

```sql
SELECT
    EXTRACT(DOW FROM order_timestamp) as day_of_week,
    EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
    COUNT(DISTINCT order_id) as order_count,
    SUM(gmv) as revenue
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": true,
    "table.cell_column": "order_count"
  }
}
```

```json metabase-pos
{ "row": 43, "col": 0, "size_x": 18, "size_y": 6 }
```

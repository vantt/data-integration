# 📘 Blueprint: CEO Monthly Scorecard

**Playbook**: [CEO Monthly Scorecard](../playbooks/ceo_monthly_scorecard.md)

> **Target Collection:** `Executive` > `Monthly Reports`
> **Role:** CEO, Board
> **Archetype:** Executive Pulse + Strategic

## 📂 Collection: Executive

Strategic dashboards for leadership — company performance, targets, and high-level KPIs.

---

### 🧊 Model: Monthly Sales Summary

Aggregated monthly sales with MoM comparison.

```sql
WITH current_month AS (
    SELECT
        COUNT(DISTINCT order_id) as total_orders,
        COALESCE(SUM(net_revenue), 0) as total_revenue,
        COALESCE(SUM(net_revenue), 0) as net_revenue,
        COUNT(DISTINCT customer_key) as unique_customers,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov,
        SUM(COALESCE(discount_amount, 0)) as total_discounts,
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as return_count
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT
        COUNT(DISTINCT order_id) as total_orders,
        COALESCE(SUM(net_revenue), 0) as total_revenue,
        COALESCE(SUM(net_revenue), 0) as net_revenue,
        COUNT(DISTINCT customer_key) as unique_customers,
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as aov
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT * FROM current_month CROSS JOIN prev_month
```

---

### 🖥️ Dashboard: CEO Monthly Scorecard

**Description**: Comprehensive monthly performance review — targets, channels, customer segments, product mix, and operational efficiency.

---

#### ❓ Question: Monthly Revenue

Total revenue for the last closed month.

**Domain Reference**: [Revenue](../domains/sales.md#1-gmv-gross-merchandise-value)

```sql
SELECT
    COALESCE(SUM(net_revenue), 0) as "Monthly Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Monthly Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 4,
  "size_y": 3
}
```

#### ❓ Question: Monthly Net Revenue

Doanh thu thuần (sau chiết khấu, trước thuế) for the last closed month.

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
SELECT
    COALESCE(SUM(net_revenue), 0) as "Monthly Net Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Monthly Net Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 4,
  "size_x": 4,
  "size_y": 3
}
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
{ "row": 0, "col": 8, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Monthly AOV

```sql
SELECT
    CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
         ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as "AOV"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "AOV": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Unique Customers

```sql
SELECT COUNT(DISTINCT customer_key) as "Unique Customers"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Revenue vs Target (Weekly Actual vs Cumulative Target)

Weekly revenue bars with cumulative target line for the closed month.

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate)

```sql
WITH weekly_actuals AS (
    SELECT
        date_trunc('week', order_timestamp)::date as week_start,
        SUM(net_revenue) as actual_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    w.week_start as "Week",
    w.actual_revenue as "Actual Revenue",
    SUM(w.actual_revenue) OVER (ORDER BY w.week_start) as "Cumulative Actual",
    t.target_revenue as "Monthly Target"
FROM weekly_actuals w
CROSS JOIN monthly_target t
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Week"],
    "graph.metrics": ["Actual Revenue", "Monthly Target"],
    "series_settings": {
      "Actual Revenue": { "display": "bar", "color": "#509EE3" },
      "Monthly Target": { "display": "line", "color": "#EF8C8C", "line.style": "dashed" }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 12,
  "size_y": 8
}
```

#### ❓ Question: 6-Month Revenue Trend

Monthly revenue for the last 6 months.

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
SELECT
    date_trunc('month', order_timestamp)::date as month,
    SUM(gross_revenue) as "Gross Revenue",
    SUM(net_revenue) as "Net Revenue"
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
    "graph.metrics": ["Gross Revenue", "Net Revenue"],
    "graph.colors": ["#509EE3", "#84BB4C"]
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 12,
  "size_x": 6,
  "size_y": 8
}
```

---

#### ❓ Question: Revenue by Channel Category

Donut chart — Ecommerce / Offline / Internal split.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_category as "Channel Category",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Channel Category",
    "pie.metric": "Revenue",
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{
  "row": 11,
  "col": 0,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: Channel Performance Table

Full channel breakdown with MoM comparison.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
WITH this_month AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) as revenue,
        COUNT(DISTINCT o.order_id) as orders,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    tm.channel_name as "Channel",
    tm.revenue as "Revenue",
    tm.orders as "Orders",
    tm.aov as "AOV",
    CASE WHEN COALESCE(lm.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tm.revenue - COALESCE(lm.revenue, 0)) * 100.0 / lm.revenue, 1) END as "MoM %"
FROM this_month tm
LEFT JOIN last_month lm ON tm.channel_name = lm.channel_name
ORDER BY tm.revenue DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND" },
      "AOV": { "number_style": "currency", "currency": "VND" },
      "MoM %": { "number_style": "percent" }
    }
  }
}
```

```json metabase-pos
{
  "row": 11,
  "col": 6,
  "size_x": 12,
  "size_y": 6
}
```

---

#### ❓ Question: Customer Segment Distribution

Customer count by RFM segment — VIP / Loyal / Regular.

**Domain Reference**: [RFM Segment](../domains/customer.md#7-rfm-segment)

```sql
SELECT
    customer_segment as "Segment",
    COUNT(*) as "Customers",
    SUM(lifetime_value) as "Total LTV"
FROM dim_customers
WHERE customer_id IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Segment",
    "pie.metric": "Customers",
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{
  "row": 17,
  "col": 0,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: New Customers (Monthly)

New customers acquired in the closed month.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
SELECT
    COUNT(DISTINCT customer_key) as "New Customers"
FROM dim_customers
WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(first_order_date) < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 17, "col": 6, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: At Risk Customers

Count of customers in At Risk or Churned status.

**Domain Reference**: [Churn Rate](../domains/customer.md#6-churn-rate)

```sql
SELECT
    customer_status as "Status",
    COUNT(*) as "Count"
FROM dim_customers
WHERE customer_status IN ('At Risk', 'Churned')
GROUP BY 1
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 17, "col": 9, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Revenue by Customer Segment

Revenue contribution by VIP / Loyal / Regular.

**Domain Reference**: [RFM Segment](../domains/customer.md#7-rfm-segment)

```sql
SELECT
    c.customer_segment as "Segment",
    SUM(o.net_revenue) as "Revenue",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Segment"],
    "graph.metrics": ["Revenue"],
    "graph.x_axis.axis_enabled": true
  }
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

---

#### ❓ Question: Top 10 Products by Revenue

Best selling products for the closed month.

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
{
  "row": 23,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: Revenue Waterfall

Gross Revenue → Discounts → Returns → Net Revenue breakdown.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact), [Return Rate](../domains/sales.md#3-return-rate--count)

```sql
SELECT
    'Gross Revenue' as "Component",
    1 as sort_order,
    SUM(gross_revenue) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    '(-) Discounts' as "Component",
    2 as sort_order,
    -SUM(COALESCE(discount_amount, 0)) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    '(-) Returns' as "Component",
    3 as sort_order,
    -SUM(CASE WHEN fulfillment_status = 'RETURNED' THEN net_revenue ELSE 0 END) as "Amount"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    '= Net Revenue' as "Component",
    4 as sort_order,
    SUM(net_revenue) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

ORDER BY sort_order
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Amount": { "number_style": "currency", "currency": "VND" }
    },
    "table.columns": [
      { "name": "Component", "enabled": true },
      { "name": "Amount", "enabled": true },
      { "name": "sort_order", "enabled": false }
    ]
  }
}
```

```json metabase-pos
{
  "row": 23,
  "col": 12,
  "size_x": 6,
  "size_y": 6
}
```

#### ❓ Question: Discount Rate

Discount as percentage of Gross Revenue for the closed month.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(net_revenue), 0), 1) as "Discount Rate %"
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
{ "row": 17, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Return Count

Returns in the closed month.

**Domain Reference**: [Return Rate](../domains/sales.md#3-return-rate--count)

```sql
SELECT
    COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as "Returns"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 17, "col": 15, "size_x": 3, "size_y": 3 }
```

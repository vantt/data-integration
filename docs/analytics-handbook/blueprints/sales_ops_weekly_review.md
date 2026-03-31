# 📘 Blueprint: Sales Ops Weekly Review

**Playbook**: [Sales Ops Weekly Review](../playbooks/sales_ops_weekly_review.md)

> **Target Collection:** `Daily Operations` > `Weekly Reports`
> **Role:** Sales Operator, Customer Support Lead
> **Archetype:** Operational Cockpit

## 📂 Collection: Operations > Periodic Reviews

Weekly and monthly operational summaries for team leads.

---

### 🖥️ Dashboard: Sales Ops Weekly Review

**Description**: Weekly operational review — order processing health, channel workload, social commerce, team performance, and payment status.

---

#### ❓ Question: Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders)

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Total GMV

**Domain Reference**: [GMV](../domains/sales.md#1-gmv-gross-merchandise-value)

```sql
SELECT COALESCE(SUM(gmv), 0) as "Total GMV"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total GMV": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 4, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: AOV

**Domain Reference**: [AOV](../domains/sales.md#5-aov-average-order-value)

```sql
SELECT
    CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
         ELSE SUM(gmv) / COUNT(DISTINCT order_id) END as "AOV"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
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
{ "row": 0, "col": 8, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Completed Orders %

Percentage of orders with COMPLETED status.

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN status = 'COMPLETED' THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Completed %"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Completed %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Order Status Distribution

Breakdown of orders by status.

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Status",
    "pie.metric": "Orders",
    "pie.show_legend": true,
    "pie.colors": {
      "COMPLETED": "#84BB4C",
      "OPEN": "#509EE3",
      "CANCELLED": "#EF8C8C",
      "ARCHIVED": "#CCCCCC"
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Fulfilment Status Breakdown

```sql
SELECT
    fulfillment_status as "Fulfilment Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
  AND fulfillment_status IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Fulfilment Status"],
    "graph.metrics": ["Orders"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Cancelled Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Cancelled Orders"
FROM fact_orders
WHERE status = 'CANCELLED'
  AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Return Count

**Domain Reference**: [Return Rate](../domains/sales.md#3-return-rate--count)

```sql
SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as "Returns"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 6, "col": 12, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Daily Orders (14 Days)

Daily order count for trend spotting.

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders)

```sql
SELECT
    date(order_timestamp) as order_date,
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE order_timestamp >= current_date - INTERVAL '14 days'
  AND order_timestamp < current_date
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["order_date"],
    "graph.metrics": ["Orders"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Peak Hour Analysis

Order count by hour × day of week for shift planning.

**Domain Reference**: [Hourly Heatmap](../domains/sales.md#7-hourly-heatmap-day-of-week-analysis)

```sql
SELECT
    EXTRACT(DOW FROM order_timestamp) as day_of_week,
    EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
    COUNT(DISTINCT order_id) as order_count
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
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
{ "row": 9, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### ❓ Question: Orders by Channel

Order count (not revenue) by channel — workload view.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Orders"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Orders by Branch

Order count per physical branch location.

```sql
SELECT
    bl.branch_location_name as "Branch",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Branch"],
    "graph.metrics": ["Orders"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 15, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Social Revenue

Revenue from Facebook + Zalo channels this week.

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume)

```sql
SELECT COALESCE(SUM(o.gmv), 0) as "Social Revenue"
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
{ "row": 21, "col": 0, "size_x": 4, "size_y": 3 }
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
{ "row": 21, "col": 4, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Top Staff by Revenue (Social Channels)

Staff leaderboard for social commerce channels.

```sql
SELECT
    st.full_name as "Staff",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE SUM(o.gmv) / COUNT(DISTINCT o.order_id) END as "AOV"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_staff st ON o.staff_key = st.staff_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  AND st.staff_key IS NOT NULL
GROUP BY 1
ORDER BY 3 DESC
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
{ "row": 21, "col": 8, "size_x": 10, "size_y": 6 }
```

---

#### ❓ Question: Staff Revenue Comparison (All Channels)

Revenue per staff member across all channels.

```sql
SELECT
    st.full_name as "Staff",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.gmv) as "Revenue"
FROM fact_orders o
JOIN dim_staff st ON o.staff_key = st.staff_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  AND st.staff_key IS NOT NULL
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Staff"],
    "graph.metrics": ["Revenue"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Payment Method Distribution

Transaction count by payment method this week.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "Payment Method",
    COUNT(*) as "Transactions",
    SUM(p.amount) as "Total Amount"
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
WHERE date(p.payment_timestamp) >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND date(p.payment_timestamp) < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Payment Method",
    "pie.metric": "Transactions"
  }
}
```

```json metabase-pos
{ "row": 33, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Payment Status Summary

**Domain Reference**: [Payment Status](../domains/sales.md#12-payment-status)

```sql
SELECT
    payment_status as "Status",
    COUNT(DISTINCT order_id) as "Orders",
    SUM(gmv) as "Total Amount"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Total Amount": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 33, "col": 6, "size_x": 12, "size_y": 6 }
```

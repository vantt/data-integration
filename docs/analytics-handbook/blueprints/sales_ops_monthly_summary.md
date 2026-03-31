# 📘 Blueprint: Sales Ops Monthly Summary

**Playbook**: [Sales Ops Monthly Summary](../playbooks/sales_ops_monthly_summary.md)

> **Target Collection:** `Operations` > `Periodic Reviews`
> **Role:** Sales Operator, Operations Manager
> **Archetype:** Operational Cockpit + Analytical

## 📂 Collection: Operations > Periodic Reviews

Weekly and monthly operational summaries for team leads.

---

### 🖥️ Dashboard: Sales Ops Monthly Summary

**Description**: Monthly operational summary — order efficiency, quality analysis, social commerce results, channel health, payment operations, and staff productivity.

---

#### ❓ Question: Monthly Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders)

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: Monthly Revenue

**Domain Reference**: [Revenue](../domains/sales.md#1-gross-revenue-gmv)

```sql
SELECT COALESCE(SUM(net_revenue), 0) as "Monthly Revenue"
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
{ "row": 0, "col": 5, "size_x": 5, "size_y": 3 }
```

#### ❓ Question: Completion Rate

Percentage of orders completed in the closed month.

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN status = 'COMPLETED' THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Completion Rate %"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Completion Rate %": { "suffix": "%", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Time to Complete

Average hours from order creation to completion.

```sql
SELECT
    ROUND(AVG(time_to_complete_hours), 1) as "Avg Hours to Complete"
FROM fact_orders
WHERE status = 'COMPLETED'
  AND time_to_complete_hours IS NOT NULL
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Avg Hours to Complete": { "suffix": " hrs", "decimals": 1 } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Order Status (MoM Comparison)

Side-by-side order status distribution: this month vs last month.

```sql
WITH this_month AS (
    SELECT status, COUNT(DISTINCT order_id) as orders
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT status, COUNT(DISTINCT order_id) as orders
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    COALESCE(tm.status, lm.status) as "Status",
    COALESCE(tm.orders, 0) as "This Month",
    COALESCE(lm.orders, 0) as "Last Month",
    CASE WHEN COALESCE(lm.orders, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tm.orders, 0) - lm.orders) * 100.0 / lm.orders, 1) END as "MoM %"
FROM this_month tm
FULL OUTER JOIN last_month lm ON tm.status = lm.status
ORDER BY COALESCE(tm.orders, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Cancellation Rate Trend (6M)

Monthly cancellation rate over 6 months.

```sql
SELECT
    date_trunc('month', order_timestamp)::date as month,
    ROUND(
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Cancellation Rate %"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Cancellation Rate %"],
    "graph.colors": ["#EF8C8C"],
    "graph.goal_value": 5,
    "graph.show_goal": true,
    "graph.goal_label": "Target < 5%"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Return Rate Trend (6M)

Monthly return rate over 6 months.

**Domain Reference**: [Return Rate](../domains/sales.md#3-return-rate--count)

```sql
SELECT
    date_trunc('month', order_timestamp)::date as month,
    ROUND(
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Return Rate %"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Return Rate %"],
    "graph.colors": ["#F9A825"],
    "graph.goal_value": 3,
    "graph.show_goal": true,
    "graph.goal_label": "Target < 3%"
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 10 Returned Products

Products with the most returns in the closed month.

```sql
SELECT
    p.product_name as "Product",
    COUNT(DISTINCT o.order_id) as "Return Count",
    SUM(o.net_revenue) as "Return Revenue"
FROM fact_orders o
JOIN fact_sales s ON o.order_id = s.order_id
JOIN dim_products p ON s.product_key = p.product_key
WHERE o.fulfillment_status = 'RETURNED'
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Return Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 9, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### ❓ Question: Cancellation by Channel

Which channels have the most cancellations?

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Cancelled Orders",
    ROUND(
        COUNT(DISTINCT o.order_id) * 100.0 / NULLIF(
            (SELECT COUNT(DISTINCT order_id) FROM fact_orders
             WHERE status = 'CANCELLED'
               AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
               AND order_timestamp < date_trunc('month', current_date)), 0
        ), 1
    ) as "% of Total Cancellations"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status = 'CANCELLED'
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
    "graph.metrics": ["Cancelled Orders"],
    "graph.x_axis.axis_enabled": true
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Social Revenue (Monthly)

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume)

```sql
SELECT COALESCE(SUM(o.net_revenue), 0) as "Social Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
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

#### ❓ Question: Social Orders (Monthly)

```sql
SELECT COUNT(DISTINCT o.order_id) as "Social Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 21, "col": 4, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Social Revenue Trend (6M)

Monthly social revenue over 6 months.

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume)

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as month,
    SUM(o.net_revenue) as "Social Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Social Revenue"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 21, "col": 8, "size_x": 10, "size_y": 6 }
```

#### ❓ Question: CS Staff Leaderboard

Monthly social commerce staff leaderboard.

```sql
SELECT
    st.full_name as "Staff",
    COUNT(DISTINCT o.order_id) as "Social Orders",
    SUM(o.net_revenue) as "Social Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as "AOV",
    ROUND(SUM(o.net_revenue) * 100.0 / NULLIF(
        (SELECT SUM(o2.net_revenue) FROM fact_orders o2
         JOIN dim_channels c2 ON o2.channel_key = c2.channel_key
         WHERE o2.status NOT IN ('CANCELLED', 'Voided')
           AND c2.platform_group IN ('Facebook', 'Zalo')
           AND o2.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
           AND o2.order_timestamp < date_trunc('month', current_date)), 0
    ), 1) as "% Contribution"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_staff st ON o.staff_key = st.staff_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
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
      "Social Revenue": { "number_style": "currency", "currency": "VND" },
      "AOV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Channel Operations Matrix

Operational health by channel — completion, cancellation, return rates.

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.net_revenue) as "Revenue",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'COMPLETED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) as "Completion %",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'CANCELLED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) as "Cancel %",
    ROUND(COUNT(CASE WHEN o.fulfillment_status = 'RETURNED' THEN 1 END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) as "Return %",
    ROUND(AVG(CASE WHEN o.status = 'COMPLETED' AND o.time_to_complete_hours IS NOT NULL
        THEN o.time_to_complete_hours END), 1) as "Avg Complete (hrs)"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
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
{ "row": 33, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Payment Method Mix

Transaction count by payment method for the closed month.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "Payment Method",
    COUNT(*) as "Transactions",
    SUM(p.amount) as "Total Amount"
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
WHERE date(p.payment_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(p.payment_timestamp) < date_trunc('month', current_date)
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
{ "row": 39, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Payment Method Trend (6M)

Monthly payment method distribution over 6 months.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    date_trunc('month', p.payment_timestamp)::date as month,
    pm.payment_method_name as payment_method,
    COUNT(*) as transactions
FROM fact_payments p
JOIN dim_payment_methods pm ON p.payment_method_key = pm.payment_method_key
WHERE date(p.payment_timestamp) >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND date(p.payment_timestamp) < date_trunc('month', current_date)
GROUP BY 1, 2
ORDER BY 1, 3 DESC
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["transactions"],
    "stackable.stack_type": "stacked"
  }
}
```

```json metabase-pos
{ "row": 39, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### ❓ Question: Payment Status Summary

**Domain Reference**: [Payment Status](../domains/sales.md#12-payment-status)

```sql
SELECT
    payment_status as "Status",
    COUNT(DISTINCT order_id) as "Orders",
    SUM(net_revenue) as "Total Amount",
    ROUND(COUNT(DISTINCT order_id) * 100.0 / NULLIF(
        (SELECT COUNT(DISTINCT order_id) FROM fact_orders
         WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
           AND order_timestamp < date_trunc('month', current_date)), 0
    ), 1) as "% of Total"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
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
{ "row": 45, "col": 0, "size_x": 18, "size_y": 4 }
```

---

#### ❓ Question: Staff Performance Table (All Channels)

Monthly staff productivity across all channels.

```sql
SELECT
    st.full_name as "Staff",
    COUNT(DISTINCT o.order_id) as "Total Orders",
    SUM(o.net_revenue) as "Total Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as "AOV",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'COMPLETED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) as "Completion %"
FROM fact_orders o
JOIN dim_staff st ON o.staff_key = st.staff_key
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
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
      "Total Revenue": { "number_style": "currency", "currency": "VND" },
      "AOV": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 49, "col": 0, "size_x": 18, "size_y": 6 }
```

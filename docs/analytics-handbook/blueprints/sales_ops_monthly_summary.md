# Sales Ops Monthly Summary Blueprint (Redesign)

**Design Spec**: [Sales Ops Monthly Summary (Redesign)](../designs/sales_ops_monthly_summary.md)
**Playbook**: [Sales Ops Monthly Summary](../playbooks/sales_ops_monthly_summary.md)

Redesigned dashboard with 3 tabs, integrated MoM comparisons, gauge for completion rate, conditional formatting throughout. Monthly operational review for Sales Ops / Operations Manager.

## 📂 Collection: Operations > Periodic Reviews

### Dashboard: Sales Ops Monthly Summary [Retail]

**Description**: Audience: Sales Ops Lead / Operations Manager. Scope: Retail (customer_type='RETAIL'). Monthly operational summary — order efficiency, quality analysis, channel health, social commerce results, staff productivity, payment operations, monthly margin & loss-order alert. 4 tabs: Tong quan thang, Kenh & Chi nhanh, Doi ngu & Thanh toan, Margin.

---

#### Filter: Date Range

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "previousmonth"
}
```

#### Filter: Branch

```json metabase-filter
{
  "slug": "branch",
  "type": "string/="
}
```

---

### Tab: Tong quan thang

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Tháng trước: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') ||
  '  ·  MoM: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '2 months')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Review ket qua thang — doanh thu, don hang, chat luong van hanh

# Review ket qua thang — doanh thu, don hang, chat luong van hanh

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Kiem tra chat luong don hang — trang thai, thoi gian xu ly, huy/tra

# Kiem tra chat luong don hang — trang thai, thoi gian xu ly, huy/tra

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Theo doi xu huong 6 thang — cancellation va return rate vs target

# Theo doi xu huong 6 thang — cancellation va return rate vs target

```json metabase-pos
{"row": 13, "col":0, "size_x":18, "size_y":1}
```

#### Question: Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders) — Hero metric with MoM comparison.

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val as "Total Orders",
    lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ]
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":6, "size_y":3}
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Supporting KPI with MoM.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val as "Net Revenue",
    lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":6, "size_x":4, "size_y":3}
```

#### Question: AOV

**Domain Reference**: [AOV](../domains/sales.md#5-aov-average-order-value) — Supporting KPI with MoM.

```sql
WITH
this_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val as "AOV",
    lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":10, "size_x":4, "size_y":3}
```

#### Question: Completion Rate

Gauge showing order completion rate with 3 zones: green (>=90%), yellow (80-89%), red (<80%).

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN status = 'COMPLETED' THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Completion Rate %"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
  [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 80, "color": "#EF8C8C", "label": "Thap" },
      { "min": 80, "max": 90, "color": "#F9D45C", "label": "Chu y" },
      { "min": 90, "max": 100, "color": "#84BB4C", "label": "Tot" }
    ]
  }
}
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

---

#### Question: Order Status Distribution

Donut chart showing breakdown of order statuses for the closed month.

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
  [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Status",
    "pie.metric": "Orders",
    "pie.colors": {
      "COMPLETED": "#84BB4C",
      "OPEN": "#98D9D9",
      "CANCELLED": "#EF8C8C",
      "Archived": "#949AAB"
    }
  }
}
```

```json metabase-pos
{"row": 7, "col":0, "size_x":6, "size_y":6}
```

#### Question: Avg Time to Complete

Average hours from order creation to completion — with MoM comparison.

```sql
WITH
this_month AS (
    SELECT ROUND(AVG(time_to_complete_hours), 1) as val
    FROM fact_orders
    WHERE status = 'COMPLETED'
      AND time_to_complete_hours IS NOT NULL
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT ROUND(AVG(time_to_complete_hours), 1) as val
    FROM fact_orders
    WHERE status = 'COMPLETED'
      AND time_to_complete_hours IS NOT NULL
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val as "Avg Hours",
    lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "Avg Hours": { "suffix": " hrs", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{"row": 7, "col":6, "size_x":6, "size_y":6}
```

#### Question: Cancelled & Returns Summary

Cancelled and return counts with MoM comparison — formatted table with conditional highlighting.

```sql
WITH
this_month AS (
    SELECT
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) as cancelled,
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as returned
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) as cancelled,
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as returned
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT * FROM (
    SELECT
        'Cancelled' as "Type",
        tm.cancelled as "This Month",
        lm.cancelled as "Last Month",
        CASE WHEN lm.cancelled = 0 THEN NULL
             ELSE ROUND((tm.cancelled - lm.cancelled) * 100.0 / lm.cancelled, 1) END as "MoM %"
    FROM this_month tm, last_month lm
    UNION ALL
    SELECT
        'Returned' as "Type",
        tm.returned as "This Month",
        lm.returned as "Last Month",
        CASE WHEN lm.returned = 0 THEN NULL
             ELSE ROUND((tm.returned - lm.returned) * 100.0 / lm.returned, 1) END as "MoM %"
    FROM this_month tm, last_month lm
)
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{"row": 7, "col":12, "size_x":6, "size_y":6}
```

---

#### Question: Cancellation Rate Trend (6M)

Monthly cancellation rate over 6 months with target goal line.

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
  [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
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
{"row": 14, "col":0, "size_x":9, "size_y":6}
```

#### Question: Return Rate Trend (6M)

Monthly return rate over 6 months with target goal line.

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
  [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Return Rate %"],
    "graph.colors": ["#F9D45C"],
    "graph.goal_value": 3,
    "graph.show_goal": true,
    "graph.goal_label": "Target < 3%"
  }
}
```

```json metabase-pos
{"row": 14, "col":9, "size_x":9, "size_y":6}
```

#### Question: Top 10 Returned Products

Products with the most returns in the closed month — with conditional formatting on top 3.

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
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Return Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Return Count"],
        "type": "single",
        "operator": ">=",
        "value": 1,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{"row": 20, "col":0, "size_x":18, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** monthly · **Scope:** customer_type='RETAIL'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: Kenh & Chi nhanh


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') || '  ·  MoM: ' || strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' – ' || strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Xac dinh kenh chiem workload — ranking orders va revenue

# Xac dinh kenh chiem workload — ranking orders va revenue

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat van hanh kenh — completion, cancel, return rates

# Danh gia hieu suat van hanh kenh — completion, cancel, return rates

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phan tich huy don theo kenh — kenh nao huy nhieu nhat?

# Phan tich huy don theo kenh — kenh nao huy nhieu nhat?

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat chi nhanh — volume va van de can xu ly

# Danh gia hieu suat chi nhanh — volume va van de can xu ly

```json metabase-pos
{ "row": 22, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Channel

Horizontal bar — ranking channels by order volume.

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Orders"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Revenue by Channel

Horizontal bar — ranking channels by revenue.

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#88BDE6"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### Question: Channel Operations Matrix

Operational health by channel — with conditional formatting on problem areas.

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
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Completion %"],
        "type": "single",
        "operator": "<",
        "value": 85,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Cancel %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Return %"],
        "type": "single",
        "operator": ">",
        "value": 3,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### Question: Cancellation by Channel

Horizontal bar — which channels have the most cancellations.

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Cancelled Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status = 'CANCELLED'
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Cancelled Orders"],
    "graph.colors": ["#EF8C8C"]
  }
}
```

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Cancellation Share by Channel

Donut — cancellation distribution across channels.

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Cancelled Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status = 'CANCELLED'
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Channel",
    "pie.metric": "Cancelled Orders"
  }
}
```

```json metabase-pos
{ "row": 16, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### Question: Orders by Branch

Horizontal bar — ranking branches by order volume.

```sql
SELECT
    bl.branch_location_name as "Branch",
    COUNT(DISTINCT o.order_id) as "Orders"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  [[AND bl.branch_location_name = {{branch}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Branch"],
    "graph.metrics": ["Orders"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Branch Performance Table

Branch performance with conditional formatting on problem areas.

```sql
SELECT
    bl.branch_location_name as "Branch",
    COUNT(DISTINCT o.order_id) as "Orders",
    SUM(o.net_revenue) as "Revenue",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'COMPLETED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) as "Completion %",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'CANCELLED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) as "Cancel %"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  [[AND bl.branch_location_name = {{branch}}]]
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Completion %"],
        "type": "single",
        "operator": "<",
        "value": 85,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Cancel %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 23, "col": 9, "size_x": 9, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** monthly · **Scope:** customer_type='RETAIL'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: Doi ngu & Thanh toan


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') || '  ·  MoM: ' || strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' – ' || strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Theo doi hieu suat Social Commerce — revenue va nhan vien

# Theo doi hieu suat Social Commerce — revenue va nhan vien

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat nhan vien toan kenh — ranking va completion

# Danh gia hieu suat nhan vien toan kenh — ranking va completion

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiem tra xu huong thanh toan va doi soat — PTTT shift va pending alert

# Kiem tra xu huong thanh toan va doi soat — PTTT shift va pending alert

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Social Revenue

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) — with MoM.

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.order_timestamp < date_trunc('month', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val as "Social Revenue",
    lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "Social Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Social Orders

Social order count with MoM comparison.

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT o.order_id) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.order_timestamp < date_trunc('month', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT COUNT(DISTINCT o.order_id) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val as "Social Orders",
    lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 2, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Social AOV

Social channel AOV with MoM comparison.

```sql
WITH
this_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.order_timestamp < date_trunc('month', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val as "Social AOV",
    lm.val as "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "Social AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### Question: Social Revenue by Platform

Donut — Facebook vs Zalo revenue split.

```sql
SELECT
    c.channel_format as "Platform",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_format IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Platform",
    "pie.metric": "Revenue",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: CS Staff Leaderboard

Monthly social commerce staff leaderboard — with top 3 highlight.

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
           AND c2.channel_format IN ('Facebook', 'Zalo')
           AND o2.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
           AND o2.order_timestamp < date_trunc('month', current_date)), 0
    ), 1) as "% Contribution"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_staff st ON o.seller_staff_key = st.staff_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_format IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND st.staff_key IS NOT NULL
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Social Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### Question: Staff Revenue Distribution

Horizontal bar — ranking all staff by total revenue across all channels.

```sql
SELECT
    st.full_name as "Staff",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_staff st ON o.seller_staff_key = st.staff_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND st.staff_key IS NOT NULL
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Staff"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Staff Performance Table

Monthly staff productivity with conditional formatting.

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
JOIN dim_staff st ON o.seller_staff_key = st.staff_key
WHERE o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
  AND st.staff_key IS NOT NULL
  [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Total Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Completion %"],
        "type": "single",
        "operator": ">=",
        "value": 95,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Completion %"],
        "type": "single",
        "operator": "<",
        "value": 80,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 12, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### Question: Payment Method Distribution

Donut — transaction count by payment method.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "Payment Method",
    COUNT(*) as "Transactions"
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
{ "row": 19, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Payment Method Trend (6M)

Stacked area — monthly payment method distribution over 6 months.

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
    "graph.dimensions": ["month", "payment_method"],
    "graph.metrics": ["transactions"],
    "stackable.stack_type": "stacked"
  }
}
```

```json metabase-pos
{ "row": 19, "col": 6, "size_x": 12, "size_y": 6 }
```

#### Question: Payment Status Summary

Payment status with conditional formatting — flag pending > 5%.

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
  [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Total Amount": { "number_style": "currency", "currency": "VND", "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["% of Total"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#F9D45C",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### 📝 Text: Footer

Source: fact_orders · Updated monthly · Excludes incomplete current month

```json metabase-pos
{ "row": 30, "col": 0, "size_x": 18, "size_y": 1 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** monthly · **Scope:** customer_type='RETAIL'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: Margin


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') || '  ·  MoM: ' || strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' – ' || strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Phan tich bien loi nhuan theo kenh — kenh nao hieu qua nhat?

# Phan tich bien loi nhuan theo kenh — kenh nao hieu qua nhat?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Monthly Margin by Channel

Table: channel breakdown with order count, revenue, gross margin %, and MoM delta in percentage points — sorted by gross margin % DESC.

```sql
WITH
this_month AS (
    SELECT
        c.channel_name                                                        AS channel,
        COUNT(DISTINCT e.order_id)                                            AS orders_tm,
        COALESCE(SUM(e.net_revenue), 0)                                       AS revenue_tm,
        COALESCE(SUM(e.gross_profit), 0)                                      AS gp_tm,
        ROUND(
            COALESCE(SUM(e.gross_profit), 0)
            / NULLIF(SUM(e.net_revenue), 0) * 100
        , 1)                                                                  AS margin_pct_tm
    FROM fact_order_economics e
    JOIN dim_channels c ON e.channel_key = c.channel_key
    WHERE e.status NOT IN ('CANCELLED', 'Voided')
      AND e.date_key >= CAST(date_trunc('month', current_date) - INTERVAL '1 month' AS DATE)
      AND e.date_key <  CAST(date_trunc('month', current_date) AS DATE)
    GROUP BY c.channel_name
),
last_month AS (
    SELECT
        c.channel_name                                                        AS channel,
        ROUND(
            COALESCE(SUM(e.gross_profit), 0)
            / NULLIF(SUM(e.net_revenue), 0) * 100
        , 1)                                                                  AS margin_pct_lm
    FROM fact_order_economics e
    JOIN dim_channels c ON e.channel_key = c.channel_key
    WHERE e.status NOT IN ('CANCELLED', 'Voided')
      AND e.date_key >= CAST(date_trunc('month', current_date) - INTERVAL '2 months' AS DATE)
      AND e.date_key <  CAST(date_trunc('month', current_date) - INTERVAL '1 month' AS DATE)
    GROUP BY c.channel_name
)
SELECT
    tm.channel                                                AS "Channel",
    tm.orders_tm                                              AS "Orders",
    tm.revenue_tm                                             AS "Revenue",
    tm.margin_pct_tm                                          AS "Gross Margin %",
    ROUND(tm.margin_pct_tm - COALESCE(lm.margin_pct_lm, 0), 1) AS "MoM Δ pp"
FROM this_month tm
LEFT JOIN last_month lm ON tm.channel = lm.channel
ORDER BY tm.margin_pct_tm DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    },
    "table.column_formatting": [
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 20,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["MoM Δ pp"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 8 }
```

#### Question: Loss-Order Alert (Monthly)

Scalar — count of completed orders where channel_net_profit < 0 (loss-making orders), with MoM comparison.

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT order_id) AS val
    FROM fact_order_economics
    WHERE channel_net_profit < 0
      AND status NOT IN ('CANCELLED', 'Voided')
      AND date_key >= CAST(date_trunc('month', current_date) - INTERVAL '1 month' AS DATE)
      AND date_key <  CAST(date_trunc('month', current_date) AS DATE)
),
last_month AS (
    SELECT COUNT(DISTINCT order_id) AS val
    FROM fact_order_economics
    WHERE channel_net_profit < 0
      AND status NOT IN ('CANCELLED', 'Voided')
      AND date_key >= CAST(date_trunc('month', current_date) - INTERVAL '2 months' AS DATE)
      AND date_key <  CAST(date_trunc('month', current_date) - INTERVAL '1 month' AS DATE)
)
SELECT
    tm.val AS "Don Lo (thang nay)",
    lm.val AS "Thang truoc"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 6, "size_y": 3 }
```

#### 📝 Text: Footer

Source: fact_order_economics · Updated monthly · Scope: Retail · COGS from MISA — orders without COGS show gross_profit = net_revenue

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** monthly · **Scope:** customer_type='RETAIL'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


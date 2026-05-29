# Sales Ops Monthly Summary [Retail] Blueprint (Redesign)

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
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Boi canh mua vu — Seasonal Context

**Bối cảnh mùa vụ VN Retail** — ưu tiên YoY khi xem tháng có seasonal event: Tết (Jan cuối/Feb đầu) — spike orders pre-Tết, gần-zero tuần Tết, Feb chậm; 9/9 · 10/10 · **11/11** · 12/12 Shopee Mega Sale — order volume spike 3-10x; Black Friday cuối Nov. Nếu tháng có seasonal event → **ưu tiên YoY %, không trust MoM % standalone.** Đặc biệt Cancel Rate và Return Rate cũng biến động mạnh theo seasonality.

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":2}
```

#### 📝 Text: Review ket qua thang — doanh thu, don hang, chat luong van hanh

# Review ket qua thang — doanh thu, don hang, chat luong van hanh

```json metabase-pos
{"row": 4, "col":0, "size_x":18, "size_y":1}
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

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders) — Hero metric with MoM + YoY comparison.

```sql
-- YoY added 2026-05-28; dynamic filter_bounds pattern
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT COUNT(DISTINCT order_id) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND order_timestamp >= filter_bounds.p_start
      AND order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT COUNT(DISTINCT order_id) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND order_timestamp <   filter_bounds.p_start
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prior_year AS (
    SELECT COUNT(DISTINCT order_id) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND order_timestamp >= (filter_bounds.p_start - INTERVAL '12 months')
      AND order_timestamp <  (filter_bounds.p_end   - INTERVAL '12 months' + INTERVAL '1 day')
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val                                                               AS "Total Orders",
    pp.val                                                               AS "Tháng trước",
    py.val                                                               AS "Cùng kỳ năm trước",
    ROUND((tm.val - pp.val) * 100.0 / NULLIF(pp.val, 0), 1)             AS "MoM %",
    ROUND((tm.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)             AS "YoY %"
FROM this_period tm, prev_period pp, prior_year py
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":18, "size_y":3}
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Supporting KPI with MoM.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      AND status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= filter_bounds.p_start
      AND order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND order_timestamp <   filter_bounds.p_start
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val AS "Net Revenue",
    pp.val AS "Thang truoc"
FROM this_period tm, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Net Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
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
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      AND status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= filter_bounds.p_start
      AND order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND order_timestamp <   filter_bounds.p_start
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val AS "AOV",
    pp.val AS "Thang truoc"
FROM this_period tm, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "AOV": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
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
    ) AS "Completion Rate %"
FROM fact_orders
WHERE customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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
    status AS "Status",
    COUNT(DISTINCT order_id) AS "Orders"
FROM fact_orders
WHERE customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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

Average hours from order creation to completion — with MoM + YoY comparison.

```sql
-- YoY added 2026-05-28; dynamic filter_bounds pattern
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      AND status = 'COMPLETED'
      AND time_to_complete_hours IS NOT NULL
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT ROUND(AVG(time_to_complete_hours), 1) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND status = 'COMPLETED'
      AND time_to_complete_hours IS NOT NULL
      AND order_timestamp >= filter_bounds.p_start
      AND order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT ROUND(AVG(time_to_complete_hours), 1) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND status = 'COMPLETED'
      AND time_to_complete_hours IS NOT NULL
      AND order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND order_timestamp <   filter_bounds.p_start
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prior_year AS (
    SELECT ROUND(AVG(time_to_complete_hours), 1) AS val
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND status = 'COMPLETED'
      AND time_to_complete_hours IS NOT NULL
      AND order_timestamp >= (filter_bounds.p_start - INTERVAL '12 months')
      AND order_timestamp <  (filter_bounds.p_end   - INTERVAL '12 months' + INTERVAL '1 day')
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val                                                               AS "Avg Hours",
    pp.val                                                               AS "Tháng trước (hrs)",
    py.val                                                               AS "Cùng kỳ năm trước (hrs)",
    ROUND((tm.val - pp.val) * 100.0 / NULLIF(pp.val, 0), 1)             AS "MoM %",
    ROUND((tm.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)             AS "YoY %"
FROM this_period tm, prev_period pp, prior_year py
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg Hours": {
        "suffix": " hrs",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":4}
```

#### Question: Cancelled & Returns Summary

Cancelled and return counts with MoM comparison — formatted table with conditional highlighting.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) AS cancelled,
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) AS returned
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND order_timestamp >= filter_bounds.p_start
      AND order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) AS cancelled,
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) AS returned
    FROM fact_orders, filter_bounds
    WHERE customer_type = 'RETAIL'
      AND order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND order_timestamp <   filter_bounds.p_start
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT * FROM (
    SELECT
        'Cancelled' AS "Type",
        tm.cancelled AS "This Month",
        pp.cancelled AS "Last Month",
        CASE WHEN pp.cancelled = 0 THEN NULL
             ELSE ROUND((tm.cancelled - pp.cancelled) * 100.0 / pp.cancelled, 1) END AS "MoM %"
    FROM this_period tm, prev_period pp
    UNION ALL
    SELECT
        'Returned' AS "Type",
        tm.returned AS "This Month",
        pp.returned AS "Last Month",
        CASE WHEN pp.returned = 0 THEN NULL
             ELSE ROUND((tm.returned - pp.returned) * 100.0 / pp.returned, 1) END AS "MoM %"
    FROM this_period tm, prev_period pp
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
    date_trunc('month', order_timestamp)::DATE AS month,
    ROUND(
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) AS "Cancellation Rate %"
FROM fact_orders
WHERE customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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
    date_trunc('month', order_timestamp)::DATE AS month,
    ROUND(
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) AS "Return Rate %"
FROM fact_orders
WHERE customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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
    p.product_name AS "Product",
    COUNT(DISTINCT o.order_id) AS "Return Count",
    SUM(o.net_revenue) AS "Return Revenue"
FROM fact_orders o
JOIN fact_sales s ON o.order_id = s.order_id
JOIN dim_products p ON s.product_key = p.product_key
WHERE o.customer_type = 'RETAIL'
  AND o.fulfillment_status = 'RETURNED'
  [[AND {{date_range}}]]
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
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat van hanh kenh — completion, cancel, return rates

# Danh gia hieu suat van hanh kenh — completion, cancel, return rates

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phan tich huy don theo kenh — kenh nao huy nhieu nhat?

# Phan tich huy don theo kenh — kenh nao huy nhieu nhat?

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat chi nhanh — volume va van de can xu ly

# Danh gia hieu suat chi nhanh — volume va van de can xu ly

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Channel

Horizontal bar — ranking channels by order volume.

```sql
SELECT
    c.channel_name AS "Channel",
    COUNT(DISTINCT o.order_id) AS "Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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
{ "row": 4, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Revenue by Channel

Horizontal bar — ranking channels by revenue.

```sql
SELECT
    c.channel_name AS "Channel",
    SUM(o.net_revenue) AS "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.customer_type = 'RETAIL'
  AND o.status NOT IN ('CANCELLED', 'Voided')
  [[AND {{date_range}}]]
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
{ "row": 4, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### Question: Channel Operations Matrix

Operational health by channel — with conditional formatting on problem areas.

```sql
SELECT
    c.channel_name AS "Channel",
    COUNT(DISTINCT o.order_id) AS "Orders",
    SUM(o.net_revenue) AS "Revenue",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'COMPLETED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) AS "Completion %",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'CANCELLED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) AS "Cancel %",
    ROUND(COUNT(CASE WHEN o.fulfillment_status = 'RETURNED' THEN 1 END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) AS "Return %",
    ROUND(AVG(CASE WHEN o.status = 'COMPLETED' AND o.time_to_complete_hours IS NOT NULL
        THEN o.time_to_complete_hours END), 1) AS "Avg Complete (hrs)"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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
{ "row": 11, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### Question: Cancellation by Channel

Horizontal bar — which channels have the most cancellations.

```sql
SELECT
    c.channel_name AS "Channel",
    COUNT(DISTINCT o.order_id) AS "Cancelled Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.customer_type = 'RETAIL'
  AND o.status = 'CANCELLED'
  [[AND {{date_range}}]]
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
{ "row": 18, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Cancellation Share by Channel

Donut — cancellation distribution across channels.

```sql
SELECT
    c.channel_name AS "Channel",
    COUNT(DISTINCT o.order_id) AS "Cancelled Orders"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.customer_type = 'RETAIL'
  AND o.status = 'CANCELLED'
  [[AND {{date_range}}]]
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
{ "row": 18, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### Question: Orders by Branch

Horizontal bar — ranking branches by order volume.

```sql
SELECT
    bl.branch_location_name AS "Branch",
    COUNT(DISTINCT o.order_id) AS "Orders"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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
{ "row": 25, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Branch Performance Table

Branch performance with conditional formatting on problem areas.

```sql
SELECT
    bl.branch_location_name AS "Branch",
    COUNT(DISTINCT o.order_id) AS "Orders",
    SUM(o.net_revenue) AS "Revenue",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'COMPLETED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) AS "Completion %",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'CANCELLED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) AS "Cancel %"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.customer_type = 'RETAIL'
  [[AND {{date_range}}]]
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
{ "row": 25, "col": 9, "size_x": 9, "size_y": 6 }
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
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat nhan vien toan kenh — ranking va completion

# Danh gia hieu suat nhan vien toan kenh — ranking va completion

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiem tra xu huong thanh toan va doi soat — PTTT shift va pending alert

# Kiem tra xu huong thanh toan va doi soat — PTTT shift va pending alert

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Social Revenue

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) — with MoM.

```sql
WITH filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      [[AND {{date_range}}]]
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) AS val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key, filter_bounds
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= filter_bounds.p_start
      AND o.order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) AS val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key, filter_bounds
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.order_timestamp <   filter_bounds.p_start
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val AS "Social Revenue",
    pp.val AS "Thang truoc"
FROM this_period tm, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Social Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Social Orders

Social order count with MoM comparison.

```sql
WITH filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      [[AND {{date_range}}]]
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT COUNT(DISTINCT o.order_id) AS val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key, filter_bounds
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= filter_bounds.p_start
      AND o.order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT COUNT(DISTINCT o.order_id) AS val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key, filter_bounds
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.order_timestamp <   filter_bounds.p_start
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val AS "Social Orders",
    pp.val AS "Thang truoc"
FROM this_period tm, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Social AOV

Social channel AOV with MoM comparison.

```sql
WITH filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      [[AND {{date_range}}]]
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END AS val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key, filter_bounds
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= filter_bounds.p_start
      AND o.order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
      [[AND {{date_range}}]]
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END AS val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key, filter_bounds
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.order_timestamp <   filter_bounds.p_start
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tm.val AS "Social AOV",
    pp.val AS "Thang truoc"
FROM this_period tm, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Social AOV": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### Question: Social Revenue by Platform

Donut — Facebook vs Zalo revenue split.

```sql
SELECT
    c.channel_format AS "Platform",
    SUM(o.net_revenue) AS "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.customer_type = 'RETAIL'
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_format IN ('Facebook', 'Zalo')
  [[AND {{date_range}}]]
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
{ "row": 7, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: CS Staff Leaderboard

Monthly social commerce staff leaderboard — with top 3 highlight.

```sql
WITH filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.customer_type = 'RETAIL'
      AND o.status NOT IN ('CANCELLED', 'Voided')
      AND c.channel_format IN ('Facebook', 'Zalo')
      [[AND {{date_range}}]]
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
total_rev AS (
    SELECT SUM(o2.net_revenue) AS total
    FROM fact_orders o2
    JOIN dim_channels c2 ON o2.channel_key = c2.channel_key, filter_bounds
    WHERE o2.customer_type = 'RETAIL'
      AND o2.status NOT IN ('CANCELLED', 'Voided')
      AND c2.channel_format IN ('Facebook', 'Zalo')
      AND o2.order_timestamp >= filter_bounds.p_start
      AND o2.order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
)
SELECT
    st.full_name AS "Staff",
    COUNT(DISTINCT o.order_id) AS "Social Orders",
    SUM(o.net_revenue) AS "Social Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END AS "AOV",
    ROUND(SUM(o.net_revenue) * 100.0 / NULLIF((SELECT total FROM total_rev), 0), 1) AS "% Contribution"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_staff st ON o.seller_staff_key = st.staff_key, filter_bounds
WHERE o.customer_type = 'RETAIL'
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_format IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= filter_bounds.p_start
  AND o.order_timestamp <  filter_bounds.p_end + INTERVAL '1 day'
  AND st.staff_key IS NOT NULL
  [[AND {{date_range}}]]
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
{ "row": 7, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### Question: Staff Revenue Distribution

Horizontal bar — ranking all staff by total revenue across all channels.

```sql
SELECT
    st.full_name AS "Staff",
    SUM(o.net_revenue) AS "Revenue"
FROM fact_orders o
JOIN dim_staff st ON o.seller_staff_key = st.staff_key
WHERE o.customer_type = 'RETAIL'
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND st.staff_key IS NOT NULL
  [[AND {{date_range}}]]
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
{ "row": 14, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Staff Performance Table

Monthly staff productivity with conditional formatting.

```sql
SELECT
    st.full_name AS "Staff",
    COUNT(DISTINCT o.order_id) AS "Total Orders",
    SUM(o.net_revenue) AS "Total Revenue",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END AS "AOV",
    ROUND(COUNT(DISTINCT CASE WHEN o.status = 'COMPLETED' THEN o.order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 1) AS "Completion %"
FROM fact_orders o
JOIN dim_staff st ON o.seller_staff_key = st.staff_key
WHERE o.customer_type = 'RETAIL'
  AND st.staff_key IS NOT NULL
  [[AND {{date_range}}]]
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
{ "row": 14, "col": 9, "size_x": 9, "size_y": 6 }
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
{ "row": 21, "col": 0, "size_x": 6, "size_y": 6 }
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
{ "row": 21, "col": 6, "size_x": 12, "size_y": 6 }
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
{ "row": 27, "col": 0, "size_x": 18, "size_y": 5 }
```



#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** monthly · **Scope:** customer_type='RETAIL'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: Margin


#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start, MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE customer_type = 'RETAIL'
      [[AND {{date_range}}]]
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
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
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 4, "col": 0, "size_x": 18, "size_y": 8 }
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
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 6, "size_y": 3 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** monthly · **Scope:** customer_type='RETAIL'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


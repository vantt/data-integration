# Sales Ops Weekly Review Blueprint (Redesign)

**Design Spec**: [Sales Ops Weekly Review (Redesign)](../designs/sales_ops_weekly_review.md)
**Playbook**: [Sales Ops Weekly Review](../playbooks/sales_ops_weekly_review.md)

Redesigned dashboard with 3 tabs, integrated WoW comparisons, gauge for completion rate, combo-chart for daily trends, heatmap for peak hours, and conditional formatting throughout. Weekly operational review for Sales Ops / CS Lead.

## Collection: Operations > Periodic Reviews

### Dashboard: Sales Ops Weekly Review

**Description**: Weekly operational review — order processing health, channel workload, team performance, payment status. 3 tabs: Tong quan, Kenh & Chi nhanh, Doi ngu & Thanh toan.

---

#### Filter: Date Range

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past7days"
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

### Tab: Tong quan tuan

#### 📝 Text: Review ket qua tuan — doanh thu, don hang, chat luong xu ly

# Review ket qua tuan — doanh thu, don hang, chat luong xu ly

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiem tra trang thai don hang — completion rate va cancelled/returns

# Kiem tra trang thai don hang — completion rate va cancelled/returns

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phan tich xu huong 14 ngay — volume, AOV, va gio cao diem

# Phan tich xu huong 14 ngay — volume, AOV, va gio cao diem

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders) — Hero metric with WoW comparison.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tw.val as "Total Orders",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Supporting KPI with WoW.

```sql
WITH
this_week AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_week AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tw.val as "Net Revenue",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ],
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: AOV

**Domain Reference**: [AOV](../domains/sales.md#5-aov-average-order-value) — Supporting KPI with WoW.

```sql
WITH
this_week AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_week AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tw.val as "AOV",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ],
    "column_settings": {
      "AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: Completed %

Gauge showing order completion rate with 3 zones: green (>=90%), yellow (80-89%), red (<80%).

```sql
SELECT
    ROUND(
        COUNT(DISTINCT CASE WHEN status = 'COMPLETED' THEN order_id END) * 100.0
        / NULLIF(COUNT(DISTINCT order_id), 0), 1
    ) as "Completed %"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
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
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### Question: Order Status Distribution

Donut chart showing breakdown of order statuses.

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
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
    "pie.show_legend": true,
    "pie.colors": {
      "COMPLETED": "#84BB4C",
      "OPEN": "#509EE3",
      "CANCELLED": "#EF8C8C",
      "ARCHIVED": "#C2D2E9"
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Fulfilment Status Breakdown

Horizontal bar ranking fulfilment statuses by volume.

```sql
SELECT
    fulfillment_status as "Fulfilment Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
  AND fulfillment_status IS NOT NULL
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Fulfilment Status"],
    "graph.metrics": ["Orders"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 5, "col": 6, "size_x": 6, "size_y": 6 }
```

#### Question: Cancelled & Returns

Formatted table showing cancelled orders and returns with WoW change flags.

```sql
WITH
this_week AS (
    SELECT
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) as cancelled,
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as returns
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_week AS (
    SELECT
        COUNT(DISTINCT CASE WHEN status = 'CANCELLED' THEN order_id END) as cancelled,
        COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as returns
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT * FROM (
    SELECT 1 as sort, 'Don huy' as "Chi so", tw.cancelled as "Tuan nay", lw.cancelled as "Tuan truoc",
        CASE WHEN lw.cancelled = 0 THEN NULL
             ELSE ROUND((tw.cancelled - lw.cancelled) * 100.0 / lw.cancelled, 1) END as "WoW %"
    FROM this_week tw, last_week lw
    UNION ALL
    SELECT 2, 'Don tra hang', tw.returns, lw.returns,
        CASE WHEN lw.returns = 0 THEN NULL
             ELSE ROUND((tw.returns - lw.returns) * 100.0 / lw.returns, 1) END
    FROM this_week tw, last_week lw
) t ORDER BY sort
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.columns": [
      { "name": "Chi so", "enabled": true },
      { "name": "Tuan nay", "enabled": true },
      { "name": "Tuan truoc", "enabled": true },
      { "name": "WoW %", "enabled": true },
      { "name": "sort", "enabled": false }
    ],
    "table.column_formatting": [
      {
        "columns": ["WoW %"],
        "type": "single",
        "operator": ">=",
        "value": 100,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["WoW %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "WoW %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### Question: Daily Orders (14 Days)

Combo chart: daily order bars (this week blue, last week grey) + AOV line.

```sql
SELECT
    date(order_timestamp) as "Ngay",
    COUNT(DISTINCT order_id) as "Don hang",
    CASE WHEN COUNT(DISTINCT CASE WHEN status NOT IN ('CANCELLED', 'Voided') THEN order_id END) = 0 THEN 0
         ELSE SUM(CASE WHEN status NOT IN ('CANCELLED', 'Voided') THEN net_revenue ELSE 0 END)
              / COUNT(DISTINCT CASE WHEN status NOT IN ('CANCELLED', 'Voided') THEN order_id END) END as "AOV"
FROM fact_orders
WHERE order_timestamp >= current_date - INTERVAL '14 days'
  AND order_timestamp < date_trunc('week', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Don hang", "AOV"],
    "series_settings": {
      "Don hang": { "display": "bar", "color": "#509EE3" },
      "AOV": { "display": "line", "color": "#7172AD", "line.style": "dashed" }
    },
    "graph.y_axis.auto_split": true,
    "column_settings": {
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: Peak Hour Heatmap

Order intensity by hour x day of week — pivot table with conditional formatting as heatmap fallback.

```sql
SELECT
    CASE EXTRACT(DOW FROM order_timestamp)
        WHEN 0 THEN 'CN'
        WHEN 1 THEN 'T2'
        WHEN 2 THEN 'T3'
        WHEN 3 THEN 'T4'
        WHEN 4 THEN 'T5'
        WHEN 5 THEN 'T6'
        WHEN 6 THEN 'T7'
    END as "Thu",
    EXTRACT(DOW FROM order_timestamp) as dow_sort,
    LPAD(CAST(EXTRACT(HOUR FROM order_timestamp) AS VARCHAR), 2, '0') || 'h' as "Gio",
    COUNT(DISTINCT order_id) as "Don"
FROM fact_orders
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND order_timestamp < date_trunc('week', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1, 2, 3
ORDER BY 2, 3
```

```json metabase-viz
{
  "display": "pivot",
  "visualization_settings": {
    "pivot_table.column_split": {
      "rows": ["Thu"],
      "columns": ["Gio"],
      "values": ["Don"]
    },
    "table.column_formatting": [
      {
        "columns": ["Don"],
        "type": "range",
        "colors": ["#FFFFFF", "#509EE3"],
        "min_type": "all",
        "max_type": "all"
      }
    ],
    "table.columns": [
      { "name": "dow_sort", "enabled": false }
    ]
  }
}
```

```json metabase-pos
{ "row": 12, "col": 12, "size_x": 6, "size_y": 6 }
```

---

### Tab: Kenh & Chi nhanh

#### 📝 Text: Xac dinh kenh chiem workload — ranking orders va revenue

# Xac dinh kenh chiem workload — ranking orders va revenue

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: So sanh hieu suat kenh WoW — highlight bien dong > 30%

# So sanh hieu suat kenh WoW — highlight bien dong > 30%

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat chi nhanh — volume va WoW change

# Danh gia hieu suat chi nhanh — volume va WoW change

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Channel

Horizontal bar ranking channels by order volume.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_name as "Kenh",
    COUNT(DISTINCT o.order_id) as "Don hang"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Don hang"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Revenue by Channel

Horizontal bar ranking channels by revenue.

```sql
SELECT
    c.channel_name as "Kenh",
    COALESCE(SUM(o.net_revenue), 0) as "Doanh thu"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#88BDE6"],
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### Question: Channel Performance Table

Formatted table with WoW comparison — highlights channels with >30% change.

```sql
WITH
this_week AS (
    SELECT
        c.channel_name as channel,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(CASE WHEN o.status NOT IN ('CANCELLED', 'Voided') THEN o.net_revenue END), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_name as channel,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(CASE WHEN o.status NOT IN ('CANCELLED', 'Voided') THEN o.net_revenue END), 0) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel, lw.channel) as "Kenh",
    COALESCE(tw.orders, 0) as "Don hang",
    COALESCE(tw.revenue, 0) as "Doanh thu",
    CASE WHEN COALESCE(tw.orders, 0) = 0 THEN 0
         ELSE ROUND(COALESCE(tw.revenue, 0) * 1.0 / tw.orders, 0) END as "AOV",
    CASE WHEN COALESCE(lw.orders, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.orders, 0) - lw.orders) * 100.0 / lw.orders, 1) END as "Don WoW %",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.revenue, 0) - lw.revenue) * 100.0 / lw.revenue, 1) END as "DT WoW %"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel = lw.channel
ORDER BY COALESCE(tw.orders, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Don WoW %", "DT WoW %"],
        "type": "single",
        "operator": ">=",
        "value": 30,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Don WoW %", "DT WoW %"],
        "type": "single",
        "operator": "<=",
        "value": -30,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true },
      "Don WoW %": { "suffix": "%", "decimals": 1 },
      "DT WoW %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 7 }
```

---

#### Question: Orders by Branch

Horizontal bar ranking branches by order volume.

```sql
SELECT
    bl.branch_location_name as "Chi nhanh",
    COUNT(DISTINCT o.order_id) as "Don hang"
FROM fact_orders o
JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Chi nhanh"],
    "graph.metrics": ["Don hang"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Branch Performance Table

Branch performance with WoW change.

```sql
WITH
this_week AS (
    SELECT
        bl.branch_location_name as branch,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(CASE WHEN o.status NOT IN ('CANCELLED', 'Voided') THEN o.net_revenue END), 0) as revenue
    FROM fact_orders o
    JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
    WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
    GROUP BY 1
),
last_week AS (
    SELECT
        bl.branch_location_name as branch,
        COUNT(DISTINCT o.order_id) as orders,
        COALESCE(SUM(CASE WHEN o.status NOT IN ('CANCELLED', 'Voided') THEN o.net_revenue END), 0) as revenue
    FROM fact_orders o
    JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
    WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
    GROUP BY 1
)
SELECT
    COALESCE(tw.branch, lw.branch) as "Chi nhanh",
    COALESCE(tw.orders, 0) as "Don hang",
    COALESCE(tw.revenue, 0) as "Doanh thu",
    CASE WHEN COALESCE(lw.orders, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.orders, 0) - lw.orders) * 100.0 / lw.orders, 1) END as "WoW %"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.branch = lw.branch
ORDER BY COALESCE(tw.orders, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["WoW %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["WoW %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "compact": true },
      "WoW %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 16, "col": 9, "size_x": 9, "size_y": 6 }
```

---

### Tab: Doi ngu & Thanh toan

#### 📝 Text: Theo doi hieu suat Social Commerce — revenue, orders, AOV

# Theo doi hieu suat Social Commerce — revenue, orders, AOV

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Danh gia hieu suat nhan vien — ranking doanh thu va top social

# Danh gia hieu suat nhan vien — ranking doanh thu va top social

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiem tra thanh toan va doi soat — phan bo PTTT va pending alert

# Kiem tra thanh toan va doi soat — phan bo PTTT va pending alert

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Social Revenue

**Domain Reference**: [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) — Social channel revenue with WoW.

```sql
WITH
this_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.platform_group IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_week AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.platform_group IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tw.val as "Social Revenue",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ],
    "column_settings": {
      "Social Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Social Orders

**Domain Reference**: [Social Order Count](../domains/customer_support.md#2-social-order-count) — Social order count with WoW.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT o.order_id) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.platform_group IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_week AS (
    SELECT COUNT(DISTINCT o.order_id) as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.platform_group IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tw.val as "Social Orders",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Social AOV

Social channel AOV with WoW comparison.

```sql
WITH
this_week AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.platform_group IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.order_timestamp < date_trunc('week', current_date)
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
),
last_week AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as val
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND c.platform_group IN ('Facebook', 'Zalo')
      AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
      AND o.order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
)
SELECT
    tw.val as "Social AOV",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "wow",
        "type": "anotherColumn",
        "column": "Tuan truoc",
        "label": "vs tuan truoc"
      }
    ],
    "column_settings": {
      "Social AOV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### Question: Staff Revenue (All Channels)

Horizontal bar ranking staff by revenue across all channels.

```sql
SELECT
    st.full_name as "Nhan vien",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
JOIN dim_staff st ON o.staff_key = st.staff_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  AND st.staff_key IS NOT NULL
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Nhan vien"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Top Staff - Social Channels

Staff leaderboard for social commerce — formatted table with top performers highlighted.

```sql
SELECT
    st.full_name as "Nhan vien",
    COUNT(DISTINCT o.order_id) as "Don hang",
    SUM(o.net_revenue) as "Doanh thu",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_staff st ON o.staff_key = st.staff_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.platform_group IN ('Facebook', 'Zalo')
  AND o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.order_timestamp < date_trunc('week', current_date)
  AND st.staff_key IS NOT NULL
      [[AND o.branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 5, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### Question: Payment Method Distribution

Donut chart showing payment method breakdown by transaction count.

**Domain Reference**: [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution)

```sql
SELECT
    pm.payment_method_name as "Phuong thuc",
    COUNT(*) as "Giao dich"
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
    "pie.dimension": "Phuong thuc",
    "pie.metric": "Giao dich",
    "pie.show_legend": true
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Payment Status Summary

Formatted table with pending payment threshold alert (>5% = red flag).

**Domain Reference**: [Payment Status](../domains/sales.md#12-payment-status)

```sql
WITH
summary AS (
    SELECT
        payment_status as status,
        COUNT(DISTINCT order_id) as orders,
        SUM(net_revenue) as amount
    FROM fact_orders
    WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND order_timestamp < date_trunc('week', current_date)
      [[AND branch_location_key IN (SELECT branch_location_key FROM dim_branch_location WHERE branch_location_name = {{branch}})]]
    GROUP BY 1
),
total AS (
    SELECT SUM(orders) as total_orders FROM summary
)
SELECT
    s.status as "Trang thai",
    s.orders as "Don hang",
    s.amount as "So tien",
    ROUND(s.orders * 100.0 / NULLIF(t.total_orders, 0), 1) as "Ty le %"
FROM summary s, total t
ORDER BY s.orders DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Ty le %"],
        "type": "single",
        "operator": ">=",
        "value": 5,
        "color": "#F9D45C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "So tien": { "number_style": "currency", "currency": "VND", "compact": true },
      "Ty le %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 12, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### 📝 Text: Footer

Source: fact_orders · Updated weekly (Mon-Sun) · Excludes incomplete current week

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 1 }
```

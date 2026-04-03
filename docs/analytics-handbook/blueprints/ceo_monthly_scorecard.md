# 📘 Blueprint: CEO Monthly Scorecard

**Design Spec**: [CEO Monthly Scorecard](../designs/ceo_monthly_scorecard.md)
**Playbook**: [CEO Monthly Scorecard](../playbooks/ceo_monthly_scorecard.md)

> **Target Collection:** `Executive`
> **Role:** CEO, Board
> **Archetype:** Executive Pulse (3 tabs)

Comprehensive monthly performance scorecard — 3 tabs: Hiệu suất tháng (KPIs + targets + trends), Kênh & Khách hàng (channels + segments), Sản phẩm & Vận hành (products + efficiency). All KPIs have MoM comparison.

## 📂 Collection: Executive

Strategic dashboards for leadership — company performance, targets, and high-level KPIs.

---

### 🖥️ Dashboard: CEO Monthly Scorecard

**Description**: Báo cáo hiệu suất kinh doanh tháng — 3 tabs: Hiệu suất, Kênh & Khách hàng, Sản phẩm & Vận hành. MoM comparison trên tất cả KPI.

> **Filter mặc định:** Loại bỏ đơn kênh `US` (Export/B2B, 100% discount nội bộ) khỏi tất cả metrics.

---

### 📑 Tab: Hieu suat thang

#### 📝 Text: Báo cáo hiệu suất kinh doanh tháng

# Báo cáo hiệu suất kinh doanh tháng

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Theo dõi pace doanh thu theo tuần — đang ahead hay behind target?

## Theo dõi pace doanh thu theo tuần — đang ahead hay behind target?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Phân tích cấu trúc doanh thu — chiết khấu và trả hàng ăn mòn bao nhiêu?

## Phân tích cấu trúc doanh thu — chiết khấu và trả hàng ăn mòn bao nhiêu?

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Monthly Net Revenue

Hero metric — doanh thu thuần tháng qua với MoM comparison.

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Net Revenue",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ],
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
{ "row": 1, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Monthly GMV

**Domain Reference**: [GMV](../domains/sales.md#1-gross-revenue-gmv)

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "GMV",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ],
    "column_settings": {
      "GMV": {
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
{ "row": 1, "col": 6, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Monthly Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders)

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Total Orders",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Monthly AOV

**Domain Reference**: [AOV](../domains/sales.md#5-aov-average-order-value)

```sql
WITH
this_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "AOV",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ],
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
{ "row": 1, "col": 14, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Unique Customers

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Unique Customers",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Target Achievement

Revenue achievement % vs monthly target — progress bar.

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate)

```sql
WITH
mtd_actual AS (
    SELECT COALESCE(SUM(net_revenue), 0) as actual_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    a.actual_revenue as "Actual Revenue"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "progress",
  "visualization_settings": {
    "progress.color": "#84BB4C"
  }
}
```

```json metabase-pos
{ "row": 5, "col": 6, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Target Variance

Absolute gap between actual and target revenue.

**Domain Reference**: [Variance to Target](../domains/sales.md#16-variance-to-target)

```sql
WITH
mtd_actual AS (
    SELECT COALESCE(SUM(net_revenue), 0) as actual_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_revenue
    FROM fact_targets
    WHERE cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    a.actual_revenue - t.target_revenue as "Variance"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Variance": {
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
{ "row": 5, "col": 12, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Revenue vs Target (Weekly)

Weekly revenue bars with cumulative target line for the closed month.

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate)

```sql
WITH weekly_actuals AS (
    SELECT
        date_trunc('week', order_timestamp)::date as week_start,
        SUM(net_revenue) as actual_revenue
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
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
    },
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": ""
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: 6-Month Revenue Trend

Monthly Gross + Net Revenue for the last 6 months.

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
SELECT
    date_trunc('month', order_timestamp)::date as "Month",
    SUM(gross_revenue) as "Gross Revenue",
    SUM(net_revenue) as "Net Revenue"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Month"],
    "graph.metrics": ["Gross Revenue", "Net Revenue"],
    "series_settings": {
      "Gross Revenue": { "color": "#88BDE6" },
      "Net Revenue": { "color": "#509EE3" }
    },
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": ""
  }
}
```

```json metabase-pos
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Revenue Waterfall

Gross Revenue → Discounts → Returns → Net Revenue breakdown.

**Domain Reference**: [Revenue Breakdown](../domains/finance.md#3-revenue-breakdown-waterfall-components)

```sql
SELECT
    'Gross Revenue' as "Component",
    1 as sort_order,
    SUM(gross_revenue) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    'Discounts' as "Component",
    2 as sort_order,
    -SUM(COALESCE(discount_amount, 0)) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    'Returns' as "Component",
    3 as sort_order,
    -SUM(CASE WHEN fulfillment_status = 'RETURNED' THEN net_revenue ELSE 0 END) as "Amount"
FROM fact_orders
WHERE channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    'Net Revenue' as "Component",
    4 as sort_order,
    SUM(net_revenue) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

ORDER BY sort_order
```

```json metabase-viz
{
  "display": "waterfall",
  "visualization_settings": {
    "graph.dimensions": ["Component"],
    "graph.metrics": ["Amount"],
    "graph.show_values": true,
    "waterfall.increase_color": "#509EE3",
    "waterfall.decrease_color": "#EF8C8C",
    "waterfall.total_color": "#84BB4C",
    "column_settings": {
      "Amount": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      },
      "sort_order": { "show": false }
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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Kenh & Khach hang

#### 📝 Text: Đánh giá hiệu suất kênh bán hàng — kênh nào cần đẩy mạnh?

## Đánh giá hiệu suất kênh bán hàng — kênh nào cần đẩy mạnh?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Theo dõi structural shift kênh 6 tháng — Ecommerce đang lên?

## Theo dõi structural shift kênh 6 tháng — Ecommerce đang lên?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiểm tra sức khỏe danh mục khách hàng — acquisition, at-risk, churn

## Kiểm tra sức khỏe danh mục khách hàng — acquisition, at-risk, churn

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

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
  AND c.channel_name != 'US'
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
    "pie.percent_visibility": "inside",
    "pie.colors": {
      "Ecommerce": "#509EE3",
      "Offline": "#88BDE6",
      "Internal": "#A989C5"
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Channel Performance Table

Full channel breakdown with MoM comparison and conditional formatting.

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
      AND c.channel_name != 'US'
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
      AND c.channel_name != 'US'
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
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true },
      "MoM %": { "suffix": "%" }
    },
    "table.column_formatting": [
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Channel Mix Trend (6M)

Monthly revenue stacked by channel category — shows structural shift over time.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    date_trunc('month', o.order_timestamp)::date as "Month",
    c.channel_category as "Channel Category",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND c.channel_name != 'US'
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Month", "Channel Category"],
    "graph.metrics": ["Revenue"],
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": "",
    "series_settings": {
      "Ecommerce": { "color": "#509EE3" },
      "Offline": { "color": "#88BDE6" },
      "Internal": { "color": "#A989C5" }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: New Customers

New customers acquired in the closed month with MoM comparison.

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers)

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(first_order_date) < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND date(first_order_date) < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "New Customers",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: At Risk Customers

Count of customers with status At Risk.

**Domain Reference**: [Churn Rate](../domains/customer.md#6-churn-rate)

```sql
SELECT COUNT(*) as "At Risk"
FROM dim_customers
WHERE customer_status = 'At Risk'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "At Risk": { "prefix": "⚠ " }
    }
  }
}
```

```json metabase-pos
{ "row": 15, "col": 6, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Churned Customers

Count of customers with status Churned.

**Domain Reference**: [Churn Rate](../domains/customer.md#6-churn-rate)

```sql
SELECT COUNT(*) as "Churned"
FROM dim_customers
WHERE customer_status = 'Churned'
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{ "row": 15, "col": 12, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Customer Segment Distribution

Customer count by RFM segment — VIP / Loyal / Regular.

**Domain Reference**: [RFM Segment](../domains/customer.md#7-rfm-segment)

```sql
SELECT
    customer_segment as "Segment",
    COUNT(*) as "Customers"
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
    "pie.percent_visibility": "inside",
    "pie.colors": {
      "VIP": "#509EE3",
      "Loyal": "#88BDE6",
      "Regular": "#A989C5"
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Revenue by Customer Segment

Revenue contribution by VIP / Loyal / Regular — horizontal bar.

**Domain Reference**: [RFM Segment](../domains/customer.md#7-rfm-segment)

```sql
SELECT
    c.customer_segment as "Segment",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.status NOT IN ('CANCELLED', 'Voided')
  AND o.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND o.order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.order_timestamp < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Segment"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5"],
    "column_settings": {
      "Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 6, "size_x": 12, "size_y": 6 }
```

---

### 📑 Tab: San pham & Van hanh

#### 📝 Text: Xác định sản phẩm và thương hiệu drive growth

## Xác định sản phẩm và thương hiệu drive growth

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiểm soát hiệu quả vận hành — chiết khấu, trả hàng có trong tầm?

## Kiểm soát hiệu quả vận hành — chiết khấu, trả hàng có trong tầm?

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top 10 Products by Revenue

Best selling products for the closed month with MoM comparison.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
WITH this_month AS (
    SELECT
        p.product_name,
        p.brand_name,
        SUM(s.quantity) as units,
        SUM(s.revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE s.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND date(s.sol_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(s.sol_timestamp) < date_trunc('month', current_date)
    GROUP BY 1, 2
),
last_month AS (
    SELECT
        p.product_name,
        SUM(s.revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE s.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND date(s.sol_timestamp) >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND date(s.sol_timestamp) < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    tm.product_name as "Product",
    tm.brand_name as "Brand",
    tm.units as "Units",
    tm.revenue as "Revenue",
    CASE WHEN COALESCE(lm.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tm.revenue - COALESCE(lm.revenue, 0)) * 100.0 / lm.revenue, 1) END as "MoM %"
FROM this_month tm
LEFT JOIN last_month lm ON tm.product_name = lm.product_name
ORDER BY tm.revenue DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "MoM %": { "suffix": "%" }
    },
    "table.column_formatting": [
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 18, "size_y": 8 }
```

#### ❓ Question: Revenue by Brand

Top brands by revenue — horizontal bar chart.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.brand_name as "Brand",
    SUM(s.revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE s.channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND date(s.sol_timestamp) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(s.sol_timestamp) < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Brand"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "Revenue": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: Discount Rate

Discount as percentage of Gross Revenue with MoM comparison.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
WITH
this_month AS (
    SELECT ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Discount Rate %",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ],
    "column_settings": {
      "Discount Rate %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Total Discount Amount

Absolute discount amount in VND.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    SUM(COALESCE(discount_amount, 0)) as "Total Discount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Total Discount": {
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
{ "row": 16, "col": 6, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Return Count

Returns in the closed month with MoM comparison.

**Domain Reference**: [Return Rate](../domains/sales.md#3-return-rate--count)

```sql
WITH
this_month AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND order_timestamp < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
      AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND order_timestamp < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Returns",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
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
        "label": "vs tháng trước"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 16, "col": 12, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Revenue Breakdown Table

GMV → Discounts → Returns → Net Revenue — detailed table view.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact), [Return Rate](../domains/sales.md#3-return-rate--count)

```sql
SELECT
    'Gross Revenue' as "Component",
    1 as sort_order,
    SUM(gross_revenue) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    '(-) Discounts' as "Component",
    2 as sort_order,
    -SUM(COALESCE(discount_amount, 0)) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    '(-) Returns' as "Component",
    3 as sort_order,
    -SUM(CASE WHEN fulfillment_status = 'RETURNED' THEN net_revenue ELSE 0 END) as "Amount"
FROM fact_orders
WHERE channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

UNION ALL

SELECT
    '= Net Revenue' as "Component",
    4 as sort_order,
    SUM(net_revenue) as "Amount"
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')
  AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND order_timestamp < date_trunc('month', current_date)

ORDER BY sort_order
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
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
{ "row": 19, "col": 0, "size_x": 18, "size_y": 4 }
```

#### 📝 Text: Source & Freshness

Source: fact_orders · Updated monthly · Excludes US channel & cancelled orders

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 18, "size_y": 1 }
```

---
primary_scope: scope_sales
scope_indicator: "[All]"
layer: L1
uses_concepts: [scope_sales, net_revenue, gross_revenue, orders_count, aov, gross_profit, channel_net_profit, discount_amount, discount_rate, filter_has_cogs, is_active_order]
---

# 📘 Blueprint: CEO Monthly Scorecard [All]

**Scope**: scope_sales (`is_sales_channel = true`)
**Layer**: L1 - Executive
**Design Spec**: [CEO Monthly Scorecard](../designs/ceo_monthly_scorecard.md)
**Playbook**: [CEO Monthly Scorecard](../playbooks/ceo_monthly_scorecard.md)

> **UPDATED (2026-04-19):** Thêm scope indicator [All] và chuyển sang filter `is_sales_channel = true`.
> Dashboard này aggregate tất cả customer types (RETAIL + B2B) nhưng loại bỏ Internal channels.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` + `filter_has_cogs` · Layer L1 `[All]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales) · [`segments.md#filter_has_cogs`](../semantic/segments.md#filter_has_cogs)
> **Why:** Monthly scorecard provides the CEO-level full business view. Revenue: `WHERE scope_sales`. P&L metrics additionally require `has_cogs = true`.
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`gross_revenue`](../semantic/metrics.md#gross_revenue) · [`orders_count`](../semantic/metrics.md#orders_count) · [`aov`](../semantic/metrics.md#aov) · [`gross_profit`](../semantic/metrics.md#gross_profit) · [`channel_net_profit`](../semantic/metrics.md#channel_net_profit) · [`discount_amount`](../semantic/metrics.md#discount_amount) · [`discount_rate`](../semantic/metrics.md#discount_rate) · [`filter_has_cogs`](../semantic/segments.md#filter_has_cogs) · [`is_active_order`](../semantic/metrics.md#is_active_order)

Revenue/order SQL: `WHERE scope_sales`. P&L SQL: `WHERE scope_sales AND has_cogs`.
## 📂 Collection: Executive

Strategic dashboards for leadership — company performance, targets, and high-level KPIs.

---

### 🖥️ Dashboard: CEO Monthly Scorecard [All]

**Description**: Báo cáo hiệu suất kinh doanh tháng — 3 tabs: Hiệu suất, Kênh & Khách hàng, Sản phẩm & Vận hành. MoM comparison trên tất cả KPI. **Scope: All sales channels (RETAIL + B2B), excludes Internal.**

---

### 📑 Tab: Hieu suat thang

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

#### 📝 Text: Bối cảnh mùa vụ — Seasonal Context

**Bối cảnh mùa vụ VN Retail** — ưu tiên YoY khi xem tháng có seasonal event:

| Tháng | Sự kiện | Tác động |
|-------|---------|---------|
| **Jan cuối / Feb đầu** | **Tết Nguyên Đán** | Revenue spike pre-Tết → gần-zero tuần Tết → Feb chậm. MoM Feb luôn âm dù YoY có thể ổn |
| **9/9** | Shopee 9.9 Mega Sale | Revenue spike 3-10x 1-2 ngày |
| **10/10** | Shopee 10.10 Sale | Revenue spike |
| **11/11** | 11.11 Double Day | Lớn nhất năm — spike mạnh nhất |
| **12/12** | 12.12 Year-End Sale | Revenue spike, sau đó chậm pre-Tết |
| **Nov cuối** | Black Friday | Spike nhỏ hơn 11.11 |

> **Nguyên tắc đọc:** Nếu tháng hiện tại có seasonal event → **ưu tiên YoY %, không trust MoM % standalone.** Ví dụ: Feb -20% MoM có thể bình thường nếu Feb năm trước cũng có Tết.

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":5}
```

#### 📝 Text: Báo cáo hiệu suất kinh doanh tháng

# Báo cáo hiệu suất kinh doanh tháng

```json metabase-pos
{"row": 7, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Theo dõi pace doanh thu theo tuần — đang ahead hay behind target?

## Theo dõi pace doanh thu theo tuần — đang ahead hay behind target?

```json metabase-pos
{"row": 12, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Phân tích cấu trúc doanh thu — chiết khấu và trả hàng ăn mòn bao nhiêu?

## Phân tích cấu trúc doanh thu — chiết khấu và trả hàng ăn mòn bao nhiêu?

```json metabase-pos
{"row": 18, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Monthly Net Revenue

Hero metric — doanh thu thuần tháng qua với MoM + YoY comparison.

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
-- YoY added 2026-05-28: VN seasonality — Tết/megasale months must compare YoY not MoM
WITH
this_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
),
prev_year AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    tm.val                                                                              AS "Net Revenue",
    pm.val                                                                              AS "Tháng trước",
    py.val                                                                              AS "Cùng kỳ năm trước",
    ROUND((tm.val - pm.val) * 100.0 / NULLIF(pm.val, 0), 1)                            AS "MoM %",
    ROUND((tm.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)                            AS "YoY %"
FROM this_month tm, prev_month pm, prev_year py
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
{"row": 3, "col":0, "size_x":9, "size_y":4}
```

#### ❓ Question: Monthly GMV

**Domain Reference**: [GMV](../domains/sales.md#1-gross-revenue-gmv)

```sql
WITH
this_month AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
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
{"row": 7, "col":0, "size_x":6, "size_y":3}
```

#### ❓ Question: Monthly Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders)

```sql
-- YoY added 2026-05-28
WITH
this_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
),
prev_year AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    tm.val                                                               AS "Total Orders",
    pm.val                                                               AS "Tháng trước",
    py.val                                                               AS "Cùng kỳ năm trước",
    ROUND((tm.val - pm.val) * 100.0 / NULLIF(pm.val, 0), 1)             AS "MoM %",
    ROUND((tm.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)             AS "YoY %"
FROM this_month tm, prev_month pm, prev_year py
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":9, "size_x":9, "size_y":4}
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
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
prev_month AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
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
{"row": 7, "col":6, "size_x":6, "size_y":3}
```

#### ❓ Question: Unique Customers

```sql
WITH
this_month AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Unique Customers",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 7, "col":12, "size_x":6, "size_y":3}
```

#### ❓ Question: Target Achievement

Revenue achievement vs monthly target — gauge showing % of target achieved.

<!-- NOTE: Metabase `progress` widget only supports static `progress.goal` (cannot bind to query column).
     Using `gauge` instead: SQL returns achievement % (0-100+), gauge segments show red/yellow/green zones.
     Segments: <80% red (behind), 80-100% yellow (on track), ≥100% green (achieved).
     Revisit `progress` on Metabase upgrades if dynamic-goal becomes supported. -->

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate)

```sql
WITH
mtd_actual AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as actual_gmv
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_gmv
    FROM fact_targets
    WHERE metric_code = 'gmv'
      AND cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    ROUND(a.actual_gmv * 100.0 / NULLIF(t.target_gmv, 0), 1) AS "Đạt %"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,   "max": 80,  "color": "#EF8C8C", "label": "Behind" },
      { "min": 80,  "max": 100, "color": "#F9D45C", "label": "On Track" },
      { "min": 100, "max": 130, "color": "#84BB4C", "label": "Achieved" }
    ],
    "column_settings": {
      "Đạt %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{"row": 10, "col":0, "size_x":6, "size_y":3}
```

#### ❓ Question: Target Variance

Absolute gap between actual and target revenue.

**Domain Reference**: [Variance to Target](../domains/sales.md#16-variance-to-target)

```sql
WITH
mtd_actual AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as actual_gmv
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_gmv
    FROM fact_targets
    WHERE metric_code = 'gmv'
      AND cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    a.actual_gmv - t.target_gmv as "Variance"
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
{"row": 10, "col":6, "size_x":6, "size_y":3}
```

#### ❓ Question: Revenue vs Target (Weekly)

Weekly revenue bars with cumulative target line for the closed month.

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate)

```sql
WITH weekly_actuals AS (
    SELECT
        date_trunc('week', ordered_at)::date as week_start,
        SUM(gross_revenue) as actual_gmv
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
    GROUP BY 1
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_gmv
    FROM fact_targets
    WHERE metric_code = 'gmv'
      AND cycle_start_date >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND cycle_end_date < date_trunc('month', current_date)
)
SELECT
    w.week_start as "Week",
    w.actual_gmv as "Actual Revenue",
    SUM(w.actual_gmv) OVER (ORDER BY w.week_start) as "Cumulative Actual",
    t.target_gmv as "Monthly Target"
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
{"row": 13, "col":0, "size_x":12, "size_y":6}
```

#### ❓ Question: 6-Month Revenue Trend

Monthly Gross + Net Revenue for the last 6 months.

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue)

```sql
SELECT
    date_trunc('month', ordered_at)::date as "Month",
    SUM(gross_revenue) as "Gross Revenue",
    SUM(net_revenue) as "Net Revenue"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND ordered_at < date_trunc('month', current_date)
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
{"row": 13, "col":12, "size_x":6, "size_y":6}
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
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

UNION ALL

SELECT
    'Discounts' as "Component",
    2 as sort_order,
    -SUM(COALESCE(discount_amount, 0)) as "Amount"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

UNION ALL

SELECT
    'Returns' as "Component",
    3 as sort_order,
    -SUM(CASE WHEN fulfillment_status = 'RETURNED' THEN net_revenue ELSE 0 END) as "Amount"
FROM fact_orders
WHERE channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

UNION ALL

SELECT
    'Net Revenue' as "Component",
    4 as sort_order,
    SUM(net_revenue) as "Amount"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

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
{"row": 19, "col":0, "size_x":18, "size_y":6}
```

---

### Section: Monthly Profitability

#### 📝 Text: Lợi nhuận tháng — gross margin, kênh, cấu trúc chi phí

## Lợi nhuận tháng — gross margin, kênh, cấu trúc chi phí

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Monthly Gross Margin %

Gross Margin % tháng trước với target 40% — table with MoM + YoY comparison.

**Domain Reference**: [Gross Margin](../domains/finance.md#5-gross-margin)

```sql
-- YoY added 2026-05-28
-- date_key is INTEGER YYYYMMDD — use CAST(strftime(...,'%Y%m%d') AS INTEGER) for range filters
WITH
this_month AS (
    SELECT ROUND(SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100, 1) AS val
    FROM fact_order_economics
    WHERE scope_sales
      AND date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND date_key <  CAST(strftime(date_trunc('month', current_date)::DATE, '%Y%m%d') AS INTEGER)
),
prev_month AS (
    SELECT ROUND(SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100, 1) AS val
    FROM fact_order_economics
    WHERE scope_sales
      AND date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '2 months')::DATE, '%Y%m%d') AS INTEGER)
      AND date_key <  CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
),
prev_year AS (
    SELECT ROUND(SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) * 100, 1) AS val
    FROM fact_order_economics
    WHERE scope_sales
      AND date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '13 months')::DATE, '%Y%m%d') AS INTEGER)
      AND date_key <  CAST(strftime((date_trunc('month', current_date) - INTERVAL '12 months')::DATE, '%Y%m%d') AS INTEGER)
)
SELECT
    COALESCE(tm.val, 0)                                           AS "Gross Margin %",
    40                                                            AS "Target %",
    COALESCE(pm.val, 0)                                           AS "Tháng trước",
    COALESCE(py.val, 0)                                           AS "Cùng kỳ năm trước",
    ROUND(COALESCE(tm.val,0) - COALESCE(pm.val,0), 1)             AS "MoM pp",
    ROUND(COALESCE(tm.val,0) - COALESCE(py.val,0), 1)             AS "YoY pp"
FROM this_month tm, prev_month pm, prev_year py
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Gross Margin %":        { "suffix": "%", "decimals": 1 },
      "Tháng trước":           { "suffix": "%", "decimals": 1 },
      "Cùng kỳ năm trước":     { "suffix": "%", "decimals": 1 },
      "MoM pp":                { "suffix": " pp", "decimals": 1 },
      "YoY pp":                { "suffix": " pp", "decimals": 1 }
    },
    "table.pivot": false,
    "table.column_formatting": [
      { "columns": ["MoM pp"], "type": "single", "operator": ">=", "value":  1, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["MoM pp"], "type": "single", "operator": "<",  "value": -1, "color": "#EF8C8C", "highlight_row": false },
      { "columns": ["YoY pp"], "type": "single", "operator": ">=", "value":  2, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["YoY pp"], "type": "single", "operator": "<",  "value": -2, "color": "#EF8C8C", "highlight_row": false }
    ]
  }
}
```

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 4 }
```

#### ❓ Question: Channel Profitability Breakdown

Net profit tháng vs tháng trước theo kênh bán hàng — grouped bar.

**Domain Reference**: [Channel Net Profit](../domains/finance.md#6-channel-net-profit)

```sql
-- date_key is INTEGER YYYYMMDD — use CAST(strftime(...,'%Y%m%d') AS INTEGER) for range filters
WITH
this_month AS (
    SELECT
        c.channel_name,
        SUM(e.channel_net_profit) AS this_month_profit
    FROM fact_order_economics e
    JOIN dim_channels c ON e.channel_key = c.channel_key
    WHERE e.scope_sales
      AND e.date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND e.date_key <  CAST(strftime(date_trunc('month', current_date)::DATE, '%Y%m%d') AS INTEGER)
    GROUP BY c.channel_name
),
prev_month AS (
    SELECT
        c.channel_name,
        SUM(e.channel_net_profit) AS last_month_profit
    FROM fact_order_economics e
    JOIN dim_channels c ON e.channel_key = c.channel_key
    WHERE e.scope_sales
      AND e.date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '2 months')::DATE, '%Y%m%d') AS INTEGER)
      AND e.date_key <  CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
    GROUP BY c.channel_name
)
SELECT
    COALESCE(tm.channel_name, pm.channel_name) AS "Kênh",
    COALESCE(tm.this_month_profit, 0)           AS "Tháng này",
    COALESCE(pm.last_month_profit, 0)           AS "Tháng trước"
FROM this_month tm
FULL OUTER JOIN prev_month pm ON tm.channel_name = pm.channel_name
ORDER BY COALESCE(tm.this_month_profit, 0) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Kênh"],
    "graph.metrics": ["Tháng này", "Tháng trước"],
    "stackable.stack_type": null,
    "graph.colors": ["#509EE3", "#88BDE6"],
    "graph.y_axis.title_text": "Net Profit (VND)",
    "graph.x_axis.title_text": "",
    "graph.show_values": false,
    "column_settings": {
      "Tháng này": { "number_style": "currency", "currency": "VND", "compact": true },
      "Tháng trước": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 30, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: Cost Structure Breakdown

Cấu trúc chi phí tháng: %COGS, %Platform Fees, %Tax, %Shipping của Net Revenue — từ fact_order_costs (long-format).

**Domain Reference**: [Cost Structure](../domains/finance.md#10-cost-structure)

```sql
-- date_key is INTEGER YYYYMMDD — use CAST(strftime(...,'%Y%m%d') AS INTEGER) for range filters
WITH
nr AS (
    SELECT COALESCE(SUM(net_revenue), 0) AS total_net_revenue
    FROM fact_order_economics
    WHERE scope_sales
      AND date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND date_key <  CAST(strftime(date_trunc('month', current_date)::DATE, '%Y%m%d') AS INTEGER)
),
costs AS (
    SELECT
        cost_category,
        SUM(amount) AS total_cost
    FROM fact_order_costs
    WHERE channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
      AND date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND date_key <  CAST(strftime(date_trunc('month', current_date)::DATE, '%Y%m%d') AS INTEGER)
      AND cost_category IN ('COGS', 'PLATFORM_FEE', 'TAX', 'SHIPPING')
    GROUP BY cost_category
)
SELECT
    c.cost_category                                                           AS "Chi phí",
    ROUND(c.total_cost / NULLIF(nr.total_net_revenue, 0) * 100, 1)           AS "% Net Revenue",
    c.total_cost                                                              AS "Số tiền (VND)"
FROM costs c
CROSS JOIN nr
ORDER BY
    CASE c.cost_category
        WHEN 'COGS'         THEN 1
        WHEN 'PLATFORM_FEE' THEN 2
        WHEN 'TAX'          THEN 3
        WHEN 'SHIPPING'     THEN 4
        ELSE 5
    END
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Chi phí"],
    "graph.metrics": ["% Net Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "% of Net Revenue",
    "graph.show_values": true,
    "column_settings": {
      "% Net Revenue": { "suffix": "%", "decimals": 1 },
      "Số tiền (VND)": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 36, "col": 0, "size_x": 18, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics + fact_order_costs · **Cadence:** monthly · **Scope:** is_sales_channel=true
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Kenh & Khach hang

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

#### 📝 Text: Đánh giá hiệu suất kênh bán hàng — kênh nào cần đẩy mạnh?

## Đánh giá hiệu suất kênh bán hàng — kênh nào cần đẩy mạnh?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Theo dõi structural shift kênh 6 tháng — Online-Ecom đang lên?

## Theo dõi structural shift kênh 6 tháng — Online-Ecom đang lên?

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiểm tra sức khỏe danh mục khách hàng — acquisition, at-risk, churn

## Kiểm tra sức khỏe danh mục khách hàng — acquisition, at-risk, churn

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Revenue by Channel Category

Donut chart — Online-Ecommerce / Offline / Internal split.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    c.channel_category as "Channel Category",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.ordered_at < date_trunc('month', current_date)
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
      "Online-Ecommerce": "#509EE3",
      "Offline": "#88BDE6",
      "Internal": "#A989C5"
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 6 }
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
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.ordered_at < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
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
{ "row": 3, "col": 6, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Channel Mix Trend (6M)

Monthly revenue stacked by channel category — shows structural shift over time.

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel)

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as "Month",
    c.channel_category as "Channel Category",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.ordered_at < date_trunc('month', current_date)
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
      "Online-Ecommerce": { "color": "#509EE3" },
      "Offline": { "color": "#88BDE6" },
      "Internal": { "color": "#A989C5" }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 6 }
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
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 6, "size_y": 3 }
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
{ "row": 17, "col": 6, "size_x": 6, "size_y": 3 }
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
{ "row": 17, "col": 12, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Customer Segment Distribution

Customer count by value_group — VALUE_VIP / GOLD / SILVER / BRONZE.

**Domain Reference**: [RFM Segment](../domains/customer.md#7-rfm-segment)

```sql
SELECT
    value_group as "Segment",
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
      "VALUE_VIP": "#509EE3",
      "VALUE_GOLD": "#88BDE6",
      "VALUE_SILVER": "#A989C5",
      "VALUE_BRONZE": "#CFD8DC"
    }
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Revenue by Customer Segment

Revenue contribution by VALUE_VIP / GOLD / SILVER / BRONZE — horizontal bar.

**Domain Reference**: [RFM Segment](../domains/customer.md#7-rfm-segment)

```sql
SELECT
    c.value_group as "Segment",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.ordered_at < date_trunc('month', current_date)
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
{ "row": 20, "col": 6, "size_x": 12, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics + fact_order_costs · **Cadence:** monthly · **Scope:** is_sales_channel=true
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: San pham & Van hanh


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

#### 📝 Text: Xác định sản phẩm và thương hiệu drive growth

## Xác định sản phẩm và thương hiệu drive growth

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics + fact_order_costs · **Cadence:** monthly · **Scope:** is_sales_channel=true
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiểm soát hiệu quả vận hành — chiết khấu, trả hàng có trong tầm?

## Kiểm soát hiệu quả vận hành — chiết khấu, trả hàng có trong tầm?

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
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
        SUM(s.net_revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE s.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
      AND date(s.ordered_at) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(s.ordered_at) < date_trunc('month', current_date)
    GROUP BY 1, 2
),
last_month AS (
    SELECT
        p.product_name,
        SUM(s.net_revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE s.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
      AND date(s.ordered_at) >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND date(s.ordered_at) < date_trunc('month', current_date) - INTERVAL '1 month'
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
{ "row": 3, "col": 0, "size_x": 18, "size_y": 8 }
```

#### ❓ Question: Revenue by Brand

Top brands by revenue — horizontal bar chart.

**Domain Reference**: [Top Selling Products](../domains/sales.md#9-top-selling-products)

```sql
SELECT
    p.brand_name as "Brand",
    SUM(s.net_revenue) as "Revenue"
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
WHERE s.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND date(s.ordered_at) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(s.ordered_at) < date_trunc('month', current_date)
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
{ "row": 11, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: Discount Rate

Discount as percentage of Gross Revenue with MoM comparison.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
WITH
this_month AS (
    SELECT ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
prev_month AS (
    SELECT ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
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
    "column_settings": {
      "Discount Rate %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Total Discount Amount

Absolute discount amount in VND.

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact)

```sql
SELECT
    SUM(COALESCE(discount_amount, 0)) as "Total Discount"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)
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
{ "row": 18, "col": 6, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Return Count

Returns in the closed month with MoM comparison.

**Domain Reference**: [Return Rate](../domains/sales.md#3-return-rate--count)

```sql
WITH
this_month AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
prev_month AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.val as "Returns",
    pm.val as "Thang truoc"
FROM this_month tm, prev_month pm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 18, "col": 12, "size_x": 6, "size_y": 3 }
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
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

UNION ALL

SELECT
    '(-) Discounts' as "Component",
    2 as sort_order,
    -SUM(COALESCE(discount_amount, 0)) as "Amount"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

UNION ALL

SELECT
    '(-) Returns' as "Component",
    3 as sort_order,
    -SUM(CASE WHEN fulfillment_status = 'RETURNED' THEN net_revenue ELSE 0 END) as "Amount"
FROM fact_orders
WHERE channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

UNION ALL

SELECT
    '= Net Revenue' as "Component",
    4 as sort_order,
    SUM(net_revenue) as "Amount"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)

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
{ "row": 21, "col": 0, "size_x": 18, "size_y": 4 }
```


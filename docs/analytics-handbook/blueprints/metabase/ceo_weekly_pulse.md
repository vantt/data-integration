---
primary_scope: scope_sales
scope_indicator: "[All]"
layer: L1
uses_concepts: [scope_sales, filter_has_cogs, net_revenue, orders_count, aov, gross_profit, is_active_order]
---

# CEO Weekly Pulse Blueprint [All]

**Scope**: scope_sales (`is_sales_channel = true`)
**Layer**: L1 - Executive
**Design Spec**: [CEO Weekly Pulse (Redesign)](../designs/ceo_weekly_pulse.md)
**Playbook**: [CEO Weekly Pulse](../playbooks/ceo_weekly_pulse.md)

> **UPDATED (2026-04-19):** Thêm scope indicator [All] và chuyển sang filter `is_sales_channel = true`.
> Dashboard này aggregate tất cả customer types (RETAIL + B2B) nhưng loại bỏ Internal channels.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` · Layer L1 `[All]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales)
> **Why:** CEO weekly pulse shows the full company performance across all customer segments (retail + B2B + staff/KOL). This is the L1 executive view — not segmented by customer type.
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`filter_has_cogs`](../semantic/segments.md#filter_has_cogs) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`orders_count`](../semantic/metrics.md#orders_count) · [`aov`](../semantic/metrics.md#aov) · [`gross_profit`](../semantic/metrics.md#gross_profit) · [`is_active_order`](../semantic/metrics.md#is_active_order)

All SQL: `WHERE scope_sales`. Do not re-derive as `is_sales_channel = true AND status NOT IN (...)`.
## 📂 Collection: Executive

### Dashboard: CEO Weekly Pulse [All]

**Description**: 5-minute Monday morning check-in — revenue pace, channel shifts, customer health, and operational flags. 3 tabs for focused scanning.

---

### Tab: Doanh thu & Target

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Tuần này: ' ||
  strftime(date_trunc('week', current_date)::DATE, '%d/%m/%Y') || ' – ' ||
  strftime(current_date, '%d/%m/%Y') ||
  '  ·  WoW: ' ||
  strftime((date_trunc('week', current_date) - INTERVAL '7 days')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('week', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: CEO Weekly Pulse — Đánh giá tiến độ doanh thu và sức khỏe kinh doanh tuần này

# CEO Weekly Pulse — Đánh giá tiến độ doanh thu và sức khỏe kinh doanh tuần này

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Kiểm tra tiến độ target tháng — on-track hay cần điều chỉnh?

# Kiểm tra tiến độ target tháng — on-track hay cần điều chỉnh?

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":1}
```

#### 📝 Text: Theo dõi xu hướng doanh thu tuần này + tuần trước (WoW) — momentum tăng hay giảm?

# Theo dõi xu hướng doanh thu tuần này + tuần trước (WoW) — momentum tăng hay giảm?

```json metabase-pos
{"row": 10, "col":0, "size_x":18, "size_y":1}
```

#### Question: Net Revenue

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Hero metric with WoW comparison.

```sql
WITH
this_week AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND ordered_at < date_trunc('week', current_date)
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
{"row": 3, "col":0, "size_x":6, "size_y":3}
```

#### Question: Gross Revenue

**Domain Reference**: [Gross Revenue](../domains/sales.md#1-gross-revenue-gmv) — Supporting KPI with WoW.

```sql
WITH
this_week AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND ordered_at < date_trunc('week', current_date)
)
SELECT
    tw.val as "Gross Revenue",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Gross Revenue": {
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

#### Question: Total Orders

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders) — Supporting KPI with WoW.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND ordered_at < date_trunc('week', current_date)
)
SELECT
    tw.val as "Total Orders",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":10, "size_x":4, "size_y":3}
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
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as val
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND ordered_at < date_trunc('week', current_date)
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
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

---

#### Question: MTD GMV vs Target

**Domain Reference**: [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate) — Progress bar showing GMV actual vs monthly GMV target in VND.

> **⚠️ Deployment note:** `progress.goal` is a static number in Metabase — it cannot be read dynamically from a query column. Currently set to 600,000,000 which matches all months in `fact_targets`. **Redeploy only if the target value changes** in Google Sheets (not on a monthly cadence — the SQL already picks up the correct month automatically).

```sql
WITH mtd_actual AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as mtd_gmv
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date)
      AND ordered_at < current_date
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_gmv
    FROM fact_targets
    WHERE metric_code = 'gmv'
      AND cycle_start_date <= current_date
      AND cycle_end_date >= current_date
)
SELECT a.mtd_gmv AS "MTD GMV"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "progress",
  "visualization_settings": {
    "progress.goal": 600000000,
    "progress.color": "#84BB4C",
    "column_settings": {
      "[\"name\",\"MTD GMV\"]": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 7, "col":0, "size_x":12, "size_y":3}
```

#### Question: Pace Index

Revenue pace indicator: MTD Actual vs expected pace. >1.0 = Ahead, <1.0 = Behind.

```sql
WITH mtd_actual AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as mtd_gmv
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date)
      AND ordered_at < current_date
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_gmv
    FROM fact_targets
    WHERE metric_code = 'gmv'
      AND cycle_start_date <= current_date
      AND cycle_end_date >= current_date
)
SELECT
    CASE WHEN t.target_gmv = 0 THEN NULL
         ELSE ROUND(
           a.mtd_gmv / (
             t.target_gmv
             * EXTRACT(DAY FROM current_date)
             / EXTRACT(DAY FROM (date_trunc('month', current_date) + INTERVAL '1 month' - INTERVAL '1 day'))
           ), 2)
    END as "Pace Index"
FROM mtd_actual a
CROSS JOIN monthly_target t
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 0.8, "color": "#EF8C8C", "label": "Behind" },
      { "min": 0.8, "max": 1.0, "color": "#F9D45C", "label": "On Track" },
      { "min": 1.0, "max": 1.5, "color": "#84BB4C", "label": "Ahead" }
    ]
  }
}
```

```json metabase-pos
{"row": 7, "col":12, "size_x":6, "size_y":3}
```

---

#### Question: Daily Net Revenue (14 Days)

**Domain Reference**: [Net Revenue](../domains/sales.md#2-net-revenue) — Area chart showing 14-day revenue trend.

```sql
SELECT
    date(ordered_at) as order_date,
    SUM(net_revenue) as revenue
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "graph.dimensions": ["order_date"],
    "graph.metrics": ["revenue"],
    "graph.colors": ["#509EE3"],
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 11, "col":0, "size_x":18, "size_y":6}
```

---

#### 📝 Text: Danh sách đơn hàng tuần này — chi tiết theo đơn

# Danh sách đơn hàng tuần này — chi tiết theo đơn

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Đơn hàng tuần này

**Domain Reference**: [Total Orders](../domains/sales.md#4-total-orders) — Order-level detail list for the current week (Mon-to-date). Drill-down backing the revenue KPIs above.

```sql
SELECT
    o.order_id as "order_id",
    o.order_code as "Mã đơn",
    strftime(o.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%d/%m %H:%M') as "Thời gian",
    COALESCE(ch.channel_name, 'Unknown') as "Kênh",
    c.full_name as "Khách hàng",
    o.status as "Trạng thái",
    o.gross_revenue as "Gross",
    o.discount_amount as "Chiết khấu",
    o.net_revenue as "Net Revenue"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
ORDER BY o.ordered_at DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "table.columns": [
      {"name": "order_id", "enabled": false}
    ],
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Chiết khấu": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Net Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "[\"name\",\"Mã đơn\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/orders/{{Mã đơn}}"
        }
      }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 9 }
```

---

#### Question: Forecasted Month-End GMV

Linear projection: if current pace holds for the rest of the month, where does GMV land?

> **⚠️ Deployment note:** same static `progress.goal` caveat as MTD GMV vs Target — currently 600,000,000.

```sql
WITH mtd_actual AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as mtd_gmv
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date)
      AND ordered_at < current_date
)
SELECT
    ROUND(
        a.mtd_gmv
        / (
            EXTRACT(DAY FROM current_date)
            / EXTRACT(DAY FROM (date_trunc('month', current_date) + INTERVAL '1 month' - INTERVAL '1 day'))
        )
    ) as "Forecasted Month-End GMV"
FROM mtd_actual a
```

```json metabase-viz
{
  "display": "progress",
  "visualization_settings": {
    "progress.goal": 600000000,
    "progress.color": "#509EE3",
    "column_settings": {
      "[\"name\",\"Forecasted Month-End GMV\"]": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 28, "col":0, "size_x":12, "size_y":3}
```

#### Question: Cần Đạt Mỗi Ngày (Required Daily Run-Rate)

Doanh thu mỗi ngày còn lại trong tháng cần đạt để chạm target — dựa trên phần target còn thiếu chia đều cho số ngày còn lại.

```sql
WITH mtd_actual AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as mtd_gmv
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date)
      AND ordered_at < current_date
),
monthly_target AS (
    SELECT COALESCE(SUM(target_val), 0) as target_gmv
    FROM fact_targets
    WHERE metric_code = 'gmv'
      AND cycle_start_date <= current_date
      AND cycle_end_date >= current_date
),
remaining AS (
    SELECT GREATEST(
        EXTRACT(DAY FROM (date_trunc('month', current_date) + INTERVAL '1 month' - INTERVAL '1 day'))
        - EXTRACT(DAY FROM current_date),
        1
    ) as remaining_days
)
SELECT
    CASE WHEN t.target_gmv = 0 THEN NULL
         ELSE ROUND(GREATEST(t.target_gmv - a.mtd_gmv, 0) / r.remaining_days)
    END as "Required Daily Run-Rate"
FROM mtd_actual a
CROSS JOIN monthly_target t
CROSS JOIN remaining r
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Required Daily Run-Rate": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 28, "col":12, "size_x":6, "size_y":3}
```

---

#### ❓ Question: Độ tươi dữ liệu

```sql
SELECT
    CASE WHEN MAX(o.ordered_at) < now() - INTERVAL '24 hours'
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ — '
         ELSE ''
    END
    || '🕐 Đơn cuối: ' || strftime(timezone('Asia/Ho_Chi_Minh', MAX(o.ordered_at)), '%d/%m %H:%M')
    || '  ·  COGS 30d: ' || ROUND(100.0 * SUM(CASE WHEN COALESCE(e.has_cogs, FALSE) THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) || '%'
    || '  ·  MISA cuối: ' || COALESCE(strftime(timezone('Asia/Ho_Chi_Minh', MAX(CASE WHEN e.cogs_source IN ('misa', 'both') THEN o.ordered_at END)), '%d/%m'), 'chưa có')
    AS "Độ tươi dữ liệu"
FROM fact_orders o
LEFT JOIN fact_order_economics e ON o.order_id = e.order_id
WHERE o.scope_sales AND o.is_active_order
    AND o.ordered_at >= current_date - INTERVAL '30 days'
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```
<!-- text-id:trust-block -->

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** Tuần này (Mon-to-date) vs WoW (tuần trước Mon-Sun) · **Scope:** is_sales_channel=true, exclude CANCELLED/Voided · **Caveats:** has_cogs ~65% coverage (MISA window) · **Exception:** MTD GMV vs Target + Pace Index + Forecasted Month-End GMV + Required Daily Run-Rate dùng cửa sổ tháng (monthly), không theo tuần. Run-rate/Forecast là linear projection dựa trên pace hiện tại, không phải model có seasonality.
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: Kenh ban hang


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Tuần này: ' ||
  strftime(date_trunc('week', current_date)::DATE, '%d/%m/%Y') || ' – ' ||
  strftime(current_date, '%d/%m/%Y') ||
  '  ·  WoW: ' ||
  strftime((date_trunc('week', current_date) - INTERVAL '7 days')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('week', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Phân tích cấu trúc kênh bán hàng — Online-Ecom vs Offline

# Phân tích cấu trúc kênh bán hàng — Online-Ecom vs Offline

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Xác định top kênh bán hàng — ranking và biến động WoW

# Xác định top kênh bán hàng — ranking và biến động WoW

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Revenue by Channel Category

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Donut chart: Online-Ecommerce / Offline / Internal split.

```sql
SELECT
    c.channel_category as "Channel Category",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
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
    "pie.show_total": true,
    "pie.percent_visibility": "inside",
    "pie.colors": {
      "Online-Ecommerce": "#509EE3",
      "Offline": "#88BDE6",
      "Internal": "#A989C5"
    },
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Channel Category WoW Comparison

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Grouped bar: this week vs last week side-by-side.

```sql
WITH this_week AS (
    SELECT
        c.channel_category,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_category,
        SUM(o.net_revenue) as revenue
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel_category, lw.channel_category) as "Channel",
    COALESCE(tw.revenue, 0) as "This Week",
    COALESCE(lw.revenue, 0) as "Last Week"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel_category = lw.channel_category
ORDER BY COALESCE(tw.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["This Week", "Last Week"],
    "graph.colors": ["#509EE3", "#C2D2E9"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "This Week": { "number_style": "currency", "currency": "VND", "compact": true },
      "Last Week": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 12, "size_y": 6 }
```

---

#### Question: Top Channels by Revenue

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Horizontal bar ranking channels by revenue.

```sql
SELECT
    c.channel_name as "Channel",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 8
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 6 }
```

#### Question: Channel Performance Table

**Domain Reference**: [Sales by Channel](../domains/sales.md#8-sales-by-channel) — Detail table with WoW % change and conditional formatting.

```sql
WITH this_week AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
    GROUP BY 1
),
last_week AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
    GROUP BY 1
)
SELECT
    COALESCE(tw.channel_name, lw.channel_name) as "Channel",
    COALESCE(tw.orders, 0) as "Orders",
    COALESCE(tw.revenue, 0) as "Revenue",
    COALESCE(lw.orders, 0) as "LW Orders",
    COALESCE(lw.revenue, 0) as "LW Revenue",
    CASE WHEN COALESCE(lw.revenue, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(tw.revenue, 0) - lw.revenue) * 100.0 / lw.revenue, 1) END as "Revenue WoW %"
FROM this_week tw
FULL OUTER JOIN last_week lw ON tw.channel_name = lw.channel_name
ORDER BY COALESCE(tw.revenue, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Revenue WoW %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Revenue WoW %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "LW Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "Revenue WoW %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 6 }
```

---


#### ❓ Question: Độ tươi dữ liệu

```sql
SELECT
    CASE WHEN MAX(o.ordered_at) < now() - INTERVAL '24 hours'
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ — '
         ELSE ''
    END
    || '🕐 Đơn cuối: ' || strftime(timezone('Asia/Ho_Chi_Minh', MAX(o.ordered_at)), '%d/%m %H:%M')
    || '  ·  COGS 30d: ' || ROUND(100.0 * SUM(CASE WHEN COALESCE(e.has_cogs, FALSE) THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) || '%'
    || '  ·  MISA cuối: ' || COALESCE(strftime(timezone('Asia/Ho_Chi_Minh', MAX(CASE WHEN e.cogs_source IN ('misa', 'both') THEN o.ordered_at END)), '%d/%m'), 'chưa có')
    AS "Độ tươi dữ liệu"
FROM fact_orders o
LEFT JOIN fact_order_economics e ON o.order_id = e.order_id
WHERE o.scope_sales AND o.is_active_order
    AND o.ordered_at >= current_date - INTERVAL '30 days'
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```
<!-- text-id:trust-block -->

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_order_economics · **Cadence:** Tuần này (Mon-to-date) vs WoW (tuần trước Mon-Sun) · **Scope:** is_sales_channel=true, exclude CANCELLED/Voided · **Caveats:** has_cogs ~65% coverage (MISA window) · **Exception:** MTD GMV vs Target + Pace Index dùng cửa sổ tháng (monthly), không theo tuần.
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: Khach hang & Canh bao


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Tuần này: ' ||
  strftime(date_trunc('week', current_date)::DATE, '%d/%m/%Y') || ' – ' ||
  strftime(current_date, '%d/%m/%Y') ||
  '  ·  WoW: ' ||
  strftime((date_trunc('week', current_date) - INTERVAL '7 days')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('week', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Đánh giá sức khỏe khách hàng — acquisition và retention

# Đánh giá sức khỏe khách hàng — acquisition và retention

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Theo dõi tỷ lệ New vs Returning tuần này + tuần trước (WoW) — chất lượng tăng trưởng

# Theo dõi tỷ lệ New vs Returning tuần này + tuần trước (WoW) — chất lượng tăng trưởng

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Kiểm tra cảnh báo vận hành — đơn hủy, trả hàng, chiết khấu

# Kiểm tra cảnh báo vận hành — đơn hủy, trả hàng, chiết khấu

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: New Customers

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) — Hero: new customer count with WoW.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date)
      AND date(first_order_date) <= current_date
),
last_week AS (
    SELECT COUNT(DISTINCT customer_key) as val
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND date(first_order_date) < date_trunc('week', current_date)
)
SELECT
    tw.val as "New Customers",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Returning Revenue %

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) — Gauge: % revenue from returning customers. Healthy > 60%.

```sql
SELECT
    ROUND(
        SUM(CASE WHEN date(c.first_order_date) < date_trunc('week', current_date) THEN o.net_revenue ELSE 0 END) * 100.0
        / NULLIF(SUM(o.net_revenue), 0), 1
    ) as "Returning Revenue %"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('week', current_date)
  AND o.ordered_at < current_date + INTERVAL '1 day'
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 40, "color": "#EF8C8C", "label": "Low" },
      { "min": 40, "max": 60, "color": "#F9D45C", "label": "Warning" },
      { "min": 60, "max": 100, "color": "#84BB4C", "label": "Healthy" }
    ]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Returning Customers

Count of returning customers this week with WoW comparison.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT o.customer_key) as val
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
      AND date(c.first_order_date) < date_trunc('week', current_date)
),
last_week AS (
    SELECT COUNT(DISTINCT o.customer_key) as val
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
      AND date(c.first_order_date) < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT
    tw.val as "Returning Customers",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### Question: New vs Returning Orders (14 Days)

**Domain Reference**: [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) — Stacked bar: daily New vs Returning order count.

```sql
SELECT
    date(o.ordered_at) as order_date,
    CASE
        WHEN date(c.first_order_date) = date(o.ordered_at) THEN 'New'
        ELSE 'Returning'
    END as customer_type,
    COUNT(DISTINCT o.order_id) as orders
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
  AND o.ordered_at < current_date + INTERVAL '1 day'
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["order_date", "customer_type"],
    "graph.metrics": ["orders"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Orders",
    "series_settings": {
      "New": { "color": "#88BDE6" },
      "Returning": { "color": "#509EE3" }
    }
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### Question: Cancelled Orders

Cancelled order count with WoW comparison. Flag if significant increase.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE NOT is_active_order
      AND scope_sales
      AND ordered_at >= date_trunc('week', current_date)
      AND ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE NOT is_active_order
      AND scope_sales
      AND ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND ordered_at < date_trunc('week', current_date)
)
SELECT
    tw.val as "Cancelled Orders",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Return Count

Return count with WoW comparison. Flag RED if > 2x previous week.

> **Source:** `fact_order_returns` — `fulfillment_status = 'RETURNED'` trên `fact_orders` không được Sapo populate; returns được track riêng trong bảng `fact_order_returns`.

```sql
WITH
this_week AS (
    SELECT COUNT(DISTINCT r.return_id) as val
    FROM fact_order_returns r
    JOIN dim_channels c ON r.channel_key = c.channel_key
    WHERE c.is_sales_channel
      AND r.return_status = 'returned'
      AND r.returned_at >= date_trunc('week', current_date)
      AND r.returned_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT COUNT(DISTINCT r.return_id) as val
    FROM fact_order_returns r
    JOIN dim_channels c ON r.channel_key = c.channel_key
    WHERE c.is_sales_channel
      AND r.return_status = 'returned'
      AND r.returned_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND r.returned_at < date_trunc('week', current_date)
)
SELECT
    tw.val as "Returns",
    lw.val as "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 14, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Discount Rate

**Domain Reference**: [Discount Impact](../domains/sales.md#13-discount-impact) — Gauge: discount as % of Gross Revenue. RED if > 15%.

```sql
SELECT
    ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as "Discount Rate %"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('week', current_date)
  AND ordered_at < current_date + INTERVAL '1 day'
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 10, "color": "#84BB4C", "label": "Normal" },
      { "min": 10, "max": 15, "color": "#F9D45C", "label": "High" },
      { "min": 15, "max": 30, "color": "#EF8C8C", "label": "Alert" }
    ]
  }
}
```

```json metabase-pos
{ "row": 14, "col": 12, "size_x": 6, "size_y": 3 }
```

---

### Section: Profitability (P&L)

> **Scope:** `fact_order_economics` — `WHERE scope_sales AND has_cogs` · [`scope_sales`](../semantic/segments.md#scope_sales) + [`filter_has_cogs`](../semantic/segments.md#filter_has_cogs)
> **Window:** Tuần này (Mon-to-date) vs WoW (tuần trước Mon–Sun). `this_week: ordered_at >= date_trunc('week', current_date) AND < current_date + INTERVAL '1 day'` · `last_week: ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days' AND < date_trunc('week', current_date)`
> **Domain References:** [Order Gross Profit](../domains/finance.md#9-order-gross-profit), [Channel Net Profit](../domains/finance.md#10-channel-net-profit-lãi-ròng-kênh)

#### 📝 Text: Lợi nhuận tuần này — Net Profit, Gross Margin, Kênh lỗ

# Lợi nhuận tuần này — Net Profit, Gross Margin, Kênh lỗ

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Weekly Net Profit

**Domain Reference**: [Channel Net Profit](../domains/finance.md#10-channel-net-profit-lãi-ròng-kênh) — Scalar WoW: lãi ròng kênh tuần qua vs tuần trước. CEO phát hiện ngay doanh thu tăng nhưng lợi nhuận giảm (margin erosion).

```sql
WITH
this_week AS (
    SELECT COALESCE(SUM(e.channel_net_profit), 0) AS val
    FROM fact_order_economics e
    JOIN fact_orders o ON e.order_id = o.order_id
    WHERE e.scope_sales
      AND e.has_cogs
      AND e.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT COALESCE(SUM(e.channel_net_profit), 0) AS val
    FROM fact_order_economics e
    JOIN fact_orders o ON e.order_id = o.order_id
    WHERE e.scope_sales
      AND e.has_cogs
      AND e.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
)
SELECT
    tw.val AS "Net Profit",
    lw.val AS "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Net Profit": {
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
{ "row": 19, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Gross Margin %

**Domain Reference**: [Order Gross Profit](../domains/finance.md#9-order-gross-profit) — Scalar WoW: biên lợi nhuận gộp % tuần qua. Tín hiệu áp lực chi phí hoặc định giá.

```sql
WITH
this_week AS (
    SELECT
        ROUND(
            SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0),
            1
        ) AS val
    FROM fact_order_economics e
    JOIN fact_orders o ON e.order_id = o.order_id
    WHERE e.scope_sales
      AND e.has_cogs
      AND e.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
),
last_week AS (
    SELECT
        ROUND(
            SUM(e.gross_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0),
            1
        ) AS val
    FROM fact_order_economics e
    JOIN fact_orders o ON e.order_id = o.order_id
    WHERE e.scope_sales
      AND e.has_cogs
      AND e.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
      AND o.ordered_at < date_trunc('week', current_date)
)
SELECT
    tw.val AS "Gross Margin %",
    lw.val AS "Tuan truoc"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Gross Margin %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 19, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Loss-Making Channel Count

**Domain Reference**: [Channel Net Profit](../domains/finance.md#10-channel-net-profit-lãi-ròng-kênh) — Scalar alert: số kênh đang lỗ trong tuần qua. Nếu > 0 → cần điều tra ngay chiến lược giá và chi phí sàn.

```sql
SELECT COUNT(*) AS "Kenh lo"
FROM (
    SELECT e.channel_key
    FROM fact_order_economics e
    JOIN fact_orders o ON e.order_id = o.order_id
    WHERE e.scope_sales
      AND e.has_cogs
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('week', current_date)
      AND o.ordered_at < current_date + INTERVAL '1 day'
    GROUP BY e.channel_key
    HAVING SUM(e.channel_net_profit) < 0
) loss_channels
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 19, "col": 12, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Độ tươi dữ liệu

```sql
SELECT
    CASE WHEN MAX(o.ordered_at) < now() - INTERVAL '24 hours'
         THEN '⚠️ DỮ LIỆU CÓ THỂ CŨ — '
         ELSE ''
    END
    || '🕐 Đơn cuối: ' || strftime(timezone('Asia/Ho_Chi_Minh', MAX(o.ordered_at)), '%d/%m %H:%M')
    || '  ·  COGS 30d: ' || ROUND(100.0 * SUM(CASE WHEN COALESCE(e.has_cogs, FALSE) THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) || '%'
    || '  ·  MISA cuối: ' || COALESCE(strftime(timezone('Asia/Ho_Chi_Minh', MAX(CASE WHEN e.cogs_source IN ('misa', 'both') THEN o.ordered_at END)), '%d/%m'), 'chưa có')
    AS "Độ tươi dữ liệu"
FROM fact_orders o
LEFT JOIN fact_order_economics e ON o.order_id = e.order_id
WHERE o.scope_sales AND o.is_active_order
    AND o.ordered_at >= current_date - INTERVAL '30 days'
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 18, "size_y": 2 }
```
<!-- text-id:trust-block -->

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers + fact_order_economics · **Cadence:** Tuần này (Mon-to-date) vs WoW (tuần trước Mon-Sun) · **Scope:** is_sales_channel=true, exclude CANCELLED/Voided · **Caveats:** has_cogs ~65% coverage (MISA window) · **Exception:** MTD GMV vs Target + Pace Index dùng cửa sổ tháng (monthly), không theo tuần.
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 18, "size_y": 1 }
```

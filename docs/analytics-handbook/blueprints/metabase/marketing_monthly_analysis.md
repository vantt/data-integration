---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts: [scope_retail, net_revenue, orders_count, aov, discount_rate, customer_acquisition, retention_rate, is_active_order]
issues:
  - "[warn] Card: Brand Performance Summary, Top 15 Products — dùng fact_sales không có scope filter; có thể bao gồm B2B orders, làm méo product ranking theo retail"
---

# 📘 Blueprint: Marketing Monthly Analysis [Retail]

**Playbook**: [Marketing Monthly Analysis](../playbooks/marketing_monthly_analysis.md)
**Design Spec**: [Marketing Monthly Analysis Design](../designs/marketing_monthly_analysis.md)

> **Target Collection:** `Marketing & Customers`
> **Role:** Marketing Manager, Brand Manager, CMO
> **Archetype:** Operational Cockpit (4 tabs)

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
> **Why:** Monthly marketing deep-dive — channel strategy, customer acquisition, cohort retention, campaign ROI. All metrics require retail segment: B2B has no promo mechanics, acquisition is relationship-based.
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`orders_count`](../semantic/metrics.md#orders_count) · [`aov`](../semantic/metrics.md#aov) · [`discount_rate`](../semantic/metrics.md#discount_rate) · [`customer_acquisition`](../semantic/metrics.md#customer_acquisition) · [`retention_rate`](../semantic/metrics.md#retention_rate) · [`is_active_order`](../semantic/metrics.md#is_active_order)

All SQL: `WHERE scope_retail`. Do not re-derive inline — use the pre-computed `scope_retail` column which also enforces `is_sales_channel` and status filters.
## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Marketing Monthly Analysis [Retail]

**Description**: Audience: Marketing Manager / CMO. Scope: Retail customers only (scope_retail). Monthly deep dive — channel strategy, customer acquisition, cohort retention, campaign ROI, brand performance, ROI & margin. 5 tabs: Monthly Pulse, Channel & Brand, Customer Intelligence, Campaigns & Products, ROI & Margin.

<!-- Filters removed: date/all-options and string/= types don't work with native SQL template tags in DuckDB.
     Date scoping is hardcoded in each SQL (last closed month). Channel filtering would require field filters. -->

---

### 📑 Tab: Monthly Pulse

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

#### 📝 Text: Boi canh mua vu — Seasonal Context

**Bối cảnh mùa vụ VN Retail** — ưu tiên YoY khi xem tháng có seasonal event: Tết (Jan cuối/Feb đầu); 9/9 · 10/10 · **11/11** · 12/12 Shopee Mega Sale — spike 3-10x; Black Friday cuối Nov. Nếu tháng có seasonal event → **ưu tiên YoY %, không trust MoM % standalone.** Lưu ý: Attribution marketing là last-click — YoY New Customers có thể bị ảnh hưởng bởi data quality thay đổi theo năm.

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":2}
```

#### 📝 Text: Marketing Monthly Review — đánh giá toàn diện hiệu suất kênh, khách hàng, campaign

# Marketing Monthly Review — đánh giá toàn diện hiệu suất kênh, khách hàng, campaign

```json metabase-pos
{"row": 4, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Monthly Net Revenue

Monthly net revenue with MoM + YoY comparison.

```sql
-- YoY added 2026-05-28
WITH this_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
last_month AS (
    SELECT COALESCE(SUM(net_revenue), 0) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
),
prior_year AS (
    SELECT COALESCE(SUM(net_revenue), 0) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND ordered_at <  date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    tm.value                                                                        AS "Net Revenue",
    lm.value                                                                        AS "Tháng trước",
    py.value                                                                        AS "Cùng kỳ năm trước",
    CASE WHEN lm.value = 0 THEN NULL
         ELSE ROUND((tm.value - lm.value) * 100.0 / lm.value, 1) END               AS "MoM %",
    CASE WHEN py.value = 0 THEN NULL
         ELSE ROUND((tm.value - py.value) * 100.0 / py.value, 1) END               AS "YoY %"
FROM this_month tm, last_month lm, prior_year py
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
{"row": 3, "col":0, "size_x":18, "size_y":4}
```

#### ❓ Question: Monthly Total Orders

```sql
WITH this_month AS (
    SELECT COUNT(DISTINCT order_id) as value
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
last_month AS (
    SELECT COUNT(DISTINCT order_id) as value
    FROM fact_orders
    WHERE scope_sales
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.value as "Total Orders",
    CASE WHEN lm.value = 0 THEN NULL
         ELSE ROUND((tm.value - lm.value) * 100.0 / lm.value, 1) END as "MoM %"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":6, "size_x":4, "size_y":4}
```

#### ❓ Question: Monthly New Customers

```sql
-- YoY added 2026-05-28
WITH this_month AS (
    SELECT COUNT(DISTINCT customer_key) as value
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(first_order_date) < date_trunc('month', current_date)
),
last_month AS (
    SELECT COUNT(DISTINCT customer_key) as value
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND date(first_order_date) < date_trunc('month', current_date) - INTERVAL '1 month'
),
prior_year AS (
    SELECT COUNT(DISTINCT customer_key) as value
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND date(first_order_date) <  date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    tm.value                                                                        AS "New Customers",
    lm.value                                                                        AS "Tháng trước",
    py.value                                                                        AS "Cùng kỳ năm trước",
    CASE WHEN lm.value = 0 THEN NULL
         ELSE ROUND((tm.value - lm.value) * 100.0 / lm.value, 1) END               AS "MoM %",
    CASE WHEN py.value = 0 THEN NULL
         ELSE ROUND((tm.value - py.value) * 100.0 / py.value, 1) END               AS "YoY %"
FROM this_month tm, last_month lm, prior_year py
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 7, "col":0, "size_x":18, "size_y":4}
```

#### ❓ Question: Monthly AOV

```sql
WITH this_month AS (
    SELECT CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
                ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
last_month AS (
    SELECT CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
                ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.value as "AOV",
    CASE WHEN lm.value = 0 THEN NULL
         ELSE ROUND((tm.value - lm.value) * 100.0 / lm.value, 1) END as "MoM %"
FROM this_month tm, last_month lm
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
{"row": 3, "col":14, "size_x":4, "size_y":4}
```

#### ❓ Question: Discount Rate Gauge

Monthly discount rate as percentage with gauge zones.

```sql
SELECT ROUND(
    SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1
) as "Discount Rate %"
FROM fact_orders
WHERE scope_sales
  AND is_active_order
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 10, "color": "#84BB4C", "label": "Healthy" },
      { "min": 10, "max": 15, "color": "#F9D45C", "label": "Caution" },
      { "min": 15, "max": 50, "color": "#EF8C8C", "label": "High" }
    ]
  }
}
```

```json metabase-pos
{"row": 7, "col":0, "size_x":6, "size_y":5}
```

#### ❓ Question: Revenue Trend (6M)

Monthly revenue with MoM growth rate — combo chart (bar + line).

```sql
WITH monthly AS (
    SELECT
        date_trunc('month', ordered_at)::date as month,
        SUM(net_revenue) as revenue
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND ordered_at < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    m.month,
    m.revenue as "Revenue",
    CASE WHEN LAG(m.revenue) OVER (ORDER BY m.month) = 0 THEN NULL
         ELSE ROUND((m.revenue - LAG(m.revenue) OVER (ORDER BY m.month)) * 100.0
              / LAG(m.revenue) OVER (ORDER BY m.month), 1) END as "MoM Growth %"
FROM monthly m
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["Revenue", "MoM Growth %"],
    "series_settings": {
      "Revenue": { "display": "bar", "color": "#509EE3" },
      "MoM Growth %": { "display": "line", "color": "#7172AD", "line.marker_enabled": true }
    },
    "graph.y_axis.auto_split": true,
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 7, "col":6, "size_x":12, "size_y":5}
```

#### 📝 Text: Xác định kênh nào đang drive revenue — composition và MoM change

# Xác định kênh nào đang drive revenue — composition và MoM change

```json metabase-pos
{"row": 12, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Channel Revenue Share

Revenue share by channel category — donut.

```sql
SELECT
    c.channel_category as "Channel",
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
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 13, "col":0, "size_x":6, "size_y":6}
```

#### ❓ Question: Revenue by Channel (MoM)

Side-by-side comparison of channel revenue: this month vs last month.

```sql
SELECT
    c.channel_category as "Channel",
    SUM(CASE WHEN o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
                  AND o.ordered_at < date_trunc('month', current_date) THEN o.net_revenue ELSE 0 END) as "This Month",
    SUM(CASE WHEN o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
                  AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month' THEN o.net_revenue ELSE 0 END) as "Last Month"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
  AND o.ordered_at < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["This Month", "Last Month"],
    "series_settings": {
      "This Month": { "color": "#509EE3" },
      "Last Month": { "color": "#C2D2E9" }
    },
    "column_settings": {
      "This Month": { "number_style": "currency", "currency": "VND", "compact": true },
      "Last Month": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 13, "col":6, "size_x":12, "size_y":6}
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

**Source:** fact_orders + fact_marketing_spend + fact_order_economics · **Cadence:** monthly · **Scope:** scope_retail · **Caveats:** ROAS attribution last-click
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Channel & Brand

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

#### 📝 Text: Theo dõi structural shift kênh 6 tháng — Online-Ecom đang chiếm ưu thế?

# Theo dõi structural shift kênh 6 tháng — Online-Ecom đang chiếm ưu thế?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Mix Trend (6M)

Monthly revenue stacked by channel category over 6 months.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as month,
    c.channel_category as "Channel",
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
    "graph.dimensions": ["month", "Channel"],
    "graph.metrics": ["Revenue"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Đánh giá hiệu suất platform — revenue, orders, khách mới, MoM

# Đánh giá hiệu suất platform — revenue, orders, khách mới, MoM

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Platform Performance Matrix

Full platform breakdown with MoM comparison.

```sql
WITH this_month AS (
    SELECT
        c.platform,
        SUM(o.net_revenue) as revenue,
        COUNT(DISTINCT o.order_id) as orders,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as aov,
        COUNT(DISTINCT CASE WHEN date(cust.first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
                             AND date(cust.first_order_date) < date_trunc('month', current_date)
                        THEN o.customer_key END) as new_customers
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    LEFT JOIN dim_customers cust ON o.customer_key = cust.customer_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.ordered_at < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT
        c.platform,
        SUM(o.net_revenue) as revenue,
        COUNT(DISTINCT o.order_id) as orders
    FROM fact_orders o
    JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    tm.platform as "Platform",
    tm.revenue as "Revenue",
    tm.orders as "Orders",
    tm.aov as "AOV",
    tm.new_customers as "New Customers",
    CASE WHEN COALESCE(lm.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tm.revenue - COALESCE(lm.revenue, 0)) * 100.0 / lm.revenue, 1) END as "MoM Rev %",
    CASE WHEN COALESCE(lm.orders, 0) = 0 THEN NULL
         ELSE ROUND((tm.orders - COALESCE(lm.orders, 0)) * 100.0 / lm.orders, 1) END as "MoM Ord %"
FROM this_month tm
LEFT JOIN last_month lm ON tm.platform = lm.platform
ORDER BY tm.revenue DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["MoM Rev %"],
        "type": "single",
        "operator": ">=",
        "value": 10,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM Rev %"],
        "type": "single",
        "operator": "<",
        "value": -10,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["MoM Ord %"],
        "type": "single",
        "operator": ">=",
        "value": 10,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM Ord %"],
        "type": "single",
        "operator": "<",
        "value": -10,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Phân tích portfolio thương hiệu kênh — ai chiếm tỷ trọng lớn nhất?

# Phân tích portfolio thương hiệu kênh — ai chiếm tỷ trọng lớn nhất?

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Brand Revenue

Top channel brands ranked by revenue.

```sql
SELECT
    c.channel_brand as "Channel Brand",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.ordered_at < date_trunc('month', current_date)
  AND c.channel_brand IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel Brand"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Revenue by Market

Domestic vs Export revenue split.

```sql
SELECT
    c.market as "Market",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.ordered_at < date_trunc('month', current_date)
  AND c.market IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 17, "col": 12, "size_x": 6, "size_y": 6 }
```

#### 📝 Text: Xác định brand tăng trưởng và brand cần đẩy mạnh marketing

# Xác định brand tăng trưởng và brand cần đẩy mạnh marketing

```json metabase-pos
{ "row": 23, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Brand Performance Summary

Product brand performance with MoM comparison.

```sql
WITH this_month AS (
    SELECT
        p.brand_name,
        SUM(s.net_revenue) as revenue,
        SUM(s.quantity) as units,
        COUNT(DISTINCT s.order_id) as order_count
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE date(s.ordered_at) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(s.ordered_at) < date_trunc('month', current_date)
    GROUP BY 1
),
last_month AS (
    SELECT
        p.brand_name,
        SUM(s.net_revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE date(s.ordered_at) >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND date(s.ordered_at) < date_trunc('month', current_date) - INTERVAL '1 month'
    GROUP BY 1
)
SELECT
    COALESCE(tm.brand_name, 'Unknown') as "Brand",
    tm.revenue as "Revenue",
    tm.units as "Units",
    tm.order_count as "Orders",
    CASE WHEN tm.order_count = 0 THEN 0
         ELSE ROUND(tm.revenue / tm.order_count) END as "AOV",
    CASE WHEN COALESCE(lm.revenue, 0) = 0 THEN NULL
         ELSE ROUND((tm.revenue - COALESCE(lm.revenue, 0)) * 100.0 / lm.revenue, 1) END as "MoM %"
FROM this_month tm
LEFT JOIN last_month lm ON tm.brand_name = lm.brand_name
ORDER BY tm.revenue DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 15,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": "<",
        "value": -15,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Revenue by Channel Type (B2C vs B2B)

B2C vs B2B revenue split derived from channel_format.

```sql
SELECT
    CASE WHEN c.channel_format = 'B2B' THEN 'B2B' ELSE 'B2C' END as "Segment",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.ordered_at < date_trunc('month', current_date)
  AND c.is_sales_channel = true
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 24, "col": 12, "size_x": 6, "size_y": 6 }
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

**Source:** fact_orders + fact_marketing_spend + fact_order_economics · **Cadence:** monthly · **Scope:** scope_retail · **Caveats:** ROAS attribution last-click
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Customer Intelligence


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

#### 📝 Text: Đánh giá acquisition — khách mới có tăng và từ kênh nào?

# Đánh giá acquisition — khách mới có tăng và từ kênh nào?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: New Customers (Month)

Hero metric for customer tab with MoM.

```sql
WITH this_month AS (
    SELECT COUNT(DISTINCT customer_key) as value
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(first_order_date) < date_trunc('month', current_date)
),
last_month AS (
    SELECT COUNT(DISTINCT customer_key) as value
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND date(first_order_date) < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.value as "New Customers",
    CASE WHEN lm.value = 0 THEN NULL
         ELSE ROUND((tm.value - lm.value) * 100.0 / lm.value, 1) END as "MoM %"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Returning Customers (Month)

```sql
WITH this_month AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.ordered_at < date_trunc('month', current_date)
      AND date(c.first_order_date) < date_trunc('month', current_date) - INTERVAL '1 month'
),
last_month AS (
    SELECT COUNT(DISTINCT o.customer_key) as value
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(c.first_order_date) < date_trunc('month', current_date) - INTERVAL '2 months'
)
SELECT
    tm.value as "Returning Customers",
    CASE WHEN lm.value = 0 THEN NULL
         ELSE ROUND((tm.value - lm.value) * 100.0 / lm.value, 1) END as "MoM %"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: New Customer Revenue Share

Percentage of revenue from new customers.

```sql
WITH this_month AS (
    SELECT
        ROUND(SUM(CASE WHEN date(c.first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
                            AND date(c.first_order_date) < date_trunc('month', current_date)
                       THEN o.net_revenue ELSE 0 END) * 100.0
              / NULLIF(SUM(o.net_revenue), 0), 1) as value
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.ordered_at < date_trunc('month', current_date)
),
last_month AS (
    SELECT
        ROUND(SUM(CASE WHEN date(c.first_order_date) >= date_trunc('month', current_date) - INTERVAL '2 months'
                            AND date(c.first_order_date) < date_trunc('month', current_date) - INTERVAL '1 month'
                       THEN o.net_revenue ELSE 0 END) * 100.0
              / NULLIF(SUM(o.net_revenue), 0), 1) as value
    FROM fact_orders o
    LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND o.ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.value as "New Customer Rev %",
    ROUND(tm.value - lm.value, 1) as "MoM pp Change"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "New Customer Rev %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: New Customer Acquisition Trend (6M)

Monthly new customers with MoM growth rate — combo chart.

```sql
WITH monthly AS (
    SELECT
        date_trunc('month', first_order_date)::date as month,
        COUNT(DISTINCT customer_key) as new_customers
    FROM dim_customers
    WHERE date(first_order_date) >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND date(first_order_date) < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    m.month,
    m.new_customers as "New Customers",
    CASE WHEN LAG(m.new_customers) OVER (ORDER BY m.month) = 0 THEN NULL
         ELSE ROUND((m.new_customers - LAG(m.new_customers) OVER (ORDER BY m.month)) * 100.0
              / LAG(m.new_customers) OVER (ORDER BY m.month), 1) END as "MoM Growth %"
FROM monthly m
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["month"],
    "graph.metrics": ["New Customers", "MoM Growth %"],
    "series_settings": {
      "New Customers": { "display": "bar", "color": "#509EE3" },
      "MoM Growth %": { "display": "line", "color": "#7172AD", "line.marker_enabled": true }
    },
    "graph.y_axis.auto_split": true
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: New Customers by Channel

Which channels acquired the most new customers this month?

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.customer_key) as "New Customers"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.scope_sales
  AND o.is_active_order
  AND date(cust.first_order_date) >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND date(cust.first_order_date) < date_trunc('month', current_date)
  AND date(cust.first_order_date) = date(o.ordered_at)
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.ordered_at < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["New Customers"],
    "graph.colors": ["#88BDE6"]
  }
}
```

```json metabase-pos
{ "row": 7, "col": 12, "size_x": 6, "size_y": 6 }
```

#### 📝 Text: Kiểm tra sức khỏe segment và retention — churn có kiểm soát?

# Kiểm tra sức khỏe segment và retention — churn có kiểm soát?

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: At Risk Customers

Count of at-risk customers with MoM change.

```sql
WITH current_count AS (
    SELECT COUNT(*) as value
    FROM dim_customers
    WHERE customer_status = 'At Risk'
),
-- Approximate last month by checking customers whose status would have been at risk
-- based on recency shifting by 30 days
prev_count AS (
    SELECT COUNT(*) as value
    FROM dim_customers
    WHERE customer_status IN ('At Risk', 'Churned')
      AND recency_days BETWEEN 61 AND 120
)
SELECT
    c.value as "At Risk Customers",
    CASE WHEN p.value = 0 THEN NULL
         ELSE ROUND((c.value - p.value) * 100.0 / p.value, 1) END as "MoM %"
FROM current_count c, prev_count p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Churn Rate Gauge

```sql
SELECT
    ROUND(
        COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) * 100.0
        / NULLIF(COUNT(*), 0), 1
    ) as "Churn Rate %"
FROM dim_customers
WHERE customer_id IS NOT NULL
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 5, "color": "#84BB4C", "label": "Healthy" },
      { "min": 5, "max": 15, "color": "#F9D45C", "label": "Watch" },
      { "min": 15, "max": 100, "color": "#EF8C8C", "label": "Critical" }
    ]
  }
}
```

```json metabase-pos
{ "row": 14, "col": 6, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Active Customer Rate

Percentage of customers active in last 30 days.

```sql
WITH stats AS (
    SELECT
        COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) as active,
        COUNT(*) as total
    FROM dim_customers
    WHERE customer_id IS NOT NULL
),
prev AS (
    SELECT
        COUNT(CASE WHEN recency_days BETWEEN 1 AND 60 THEN 1 END) as active,
        COUNT(*) as total
    FROM dim_customers
    WHERE customer_id IS NOT NULL
)
SELECT
    ROUND(s.active * 100.0 / NULLIF(s.total, 0), 1) as "Active Rate %",
    ROUND(s.active * 100.0 / NULLIF(s.total, 0) - p.active * 100.0 / NULLIF(p.total, 0), 1) as "MoM pp"
FROM stats s, prev p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Active Rate %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 12, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Customer Value Group Movement

Value group breakdown with customer count and LTV.

```sql
SELECT
    value_group as "Value Group",
    customer_status as "Status",
    COUNT(*) as "Customers",
    SUM(lifetime_value) as "Total LTV",
    ROUND(AVG(lifetime_value)) as "Avg LTV"
FROM dim_customers
WHERE customer_id IS NOT NULL
GROUP BY 1, 2
ORDER BY 
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 WHEN 'VALUE_SILVER' THEN 3 ELSE 4 END,
    3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Total LTV": { "number_style": "currency", "currency": "VND", "compact": true },
      "Avg LTV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Cohort Retention Heatmap

Month-over-month retention by acquisition cohort.

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
        date_diff('month', c.first_order_date, o.ordered_at) as month_number,
        COUNT(DISTINCT c.customer_id) as active_customers
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
    WHERE c.first_order_date >= (current_date - INTERVAL '12' MONTH)
      AND o.ordered_at >= c.first_order_date
      AND o.scope_sales
    GROUP BY 1, 2
)
SELECT
    strftime(r.cohort_month, '%Y-%m') as "Cohort",
    r.month_number as "Month #",
    ROUND(CAST(r.active_customers AS FLOAT) / s.original_size * 100, 1) as "Retention %"
FROM retention_activity r
JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
WHERE r.month_number <= 6
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "pivot",
  "visualization_settings": {
    "table.pivot": true,
    "table.cell_column": "Retention %",
    "pivot.show_column_totals": false,
    "pivot.show_row_totals": false,
    "table.column_formatting": [
      {
        "columns": ["Retention %"],
        "type": "range",
        "colors": ["#FFFFFF", "#509EE3"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 100
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 18, "col": 9, "size_x": 9, "size_y": 6 }
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

**Source:** fact_orders + fact_marketing_spend + fact_order_economics · **Cadence:** monthly · **Scope:** scope_retail · **Caveats:** ROAS attribution last-click
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Campaigns & Products


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

#### 📝 Text: Phân tích ROI campaign — promotion nào mang lại giá trị?

# Phân tích ROI campaign — promotion nào mang lại giá trị?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total Discount Amount

```sql
WITH this_month AS (
    SELECT COALESCE(SUM(discount_amount), 0) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
    ),
last_month AS (
    SELECT COALESCE(SUM(discount_amount), 0) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.value as "Discount Amount",
    CASE WHEN lm.value = 0 THEN NULL
         ELSE ROUND((tm.value - lm.value) * 100.0 / lm.value, 1) END as "MoM %"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Discount Amount": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Discounted Order Percentage

```sql
WITH this_month AS (
    SELECT ROUND(COUNT(CASE WHEN discount_amount > 0 THEN 1 END) * 100.0
           / NULLIF(COUNT(*), 0), 1) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
last_month AS (
    SELECT ROUND(COUNT(CASE WHEN discount_amount > 0 THEN 1 END) * 100.0
           / NULLIF(COUNT(*), 0), 1) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.value as "Discounted %",
    ROUND(tm.value - lm.value, 1) as "MoM pp"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Discounted %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Average Discount Depth

```sql
WITH this_month AS (
    SELECT ROUND(AVG(CASE WHEN discount_amount > 0
                THEN discount_amount * 100.0 / NULLIF(gross_revenue, 0) END), 1) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
),
last_month AS (
    SELECT ROUND(AVG(CASE WHEN discount_amount > 0
                THEN discount_amount * 100.0 / NULLIF(gross_revenue, 0) END), 1) as value
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND ordered_at < date_trunc('month', current_date) - INTERVAL '1 month'
)
SELECT
    tm.value as "Avg Discount %",
    ROUND(tm.value - lm.value, 1) as "MoM pp"
FROM this_month tm, last_month lm
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg Discount %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Promotion Leaderboard

Top promotions ranked by revenue.

```sql
WITH promo_orders AS (
    SELECT
        COALESCE(p.promotion_code, 'Unknown') as promo_code,
        COUNT(DISTINCT o.order_id) as usage_count,
        SUM(o.net_revenue) as revenue,
        ROUND(AVG(COALESCE(o.discount_amount, 0) * 100.0 / NULLIF(o.gross_revenue, 0)), 1) as avg_discount_pct,
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT o.order_id) END as promo_aov
    FROM fact_orders o
    JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.scope_sales
      AND o.is_active_order
      AND p.promotion_code IS NOT NULL
      AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND o.ordered_at < date_trunc('month', current_date)
    GROUP BY 1
),
baseline AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE SUM(net_revenue) / COUNT(DISTINCT order_id) END as non_promo_aov
    FROM fact_orders
    WHERE scope_sales
      AND is_active_order
      AND promotion_key IS NULL
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND ordered_at < date_trunc('month', current_date)
)
SELECT
    po.promo_code as "Promo Code",
    po.usage_count as "Usage",
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
  "visualization_settings": {
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "Promo AOV": { "number_style": "currency", "currency": "VND", "compact": true },
      "Non-Promo AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 6 }
```

#### ❓ Question: Discount Trend (6M)

Monthly discount rate with 15% goal line.

```sql
SELECT
    date_trunc('month', ordered_at)::date as month,
    ROUND(SUM(COALESCE(discount_amount, 0)) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as "Discount Rate %"
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
    "graph.dimensions": ["month"],
    "graph.metrics": ["Discount Rate %"],
    "graph.colors": ["#F9D45C"],
    "graph.goal_value": 15,
    "graph.show_goal": true,
    "graph.goal_label": "Target < 15%",
    "line.marker_enabled": true
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Revenue Discounted vs Full-Price (6M)

Monthly revenue split: discounted orders vs full-price.

```sql
SELECT
    date_trunc('month', ordered_at)::date as month,
    SUM(CASE WHEN COALESCE(discount_amount, 0) = 0 THEN net_revenue ELSE 0 END) as "Full-Price Revenue",
    SUM(CASE WHEN discount_amount > 0 THEN net_revenue ELSE 0 END) as "Discounted Revenue"
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
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["month"],
    "graph.metrics": ["Full-Price Revenue", "Discounted Revenue"],
    "series_settings": {
      "Full-Price Revenue": { "color": "#509EE3" },
      "Discounted Revenue": { "color": "#F9D45C" }
    },
    "column_settings": {
      "Full-Price Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "Discounted Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Xác định sản phẩm drive revenue và brand cần attention

# Xác định sản phẩm drive revenue và brand cần attention

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top 15 Products by Revenue

Top products with MoM comparison.

```sql
WITH this_month AS (
    SELECT
        p.product_name,
        p.brand_name,
        SUM(s.quantity) as units,
        SUM(s.net_revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE date(s.ordered_at) >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND date(s.ordered_at) < date_trunc('month', current_date)
    GROUP BY 1, 2
),
last_month AS (
    SELECT
        p.product_name,
        SUM(s.net_revenue) as revenue
    FROM fact_sales s
    JOIN dim_products p ON s.product_key = p.product_key
    WHERE date(s.ordered_at) >= date_trunc('month', current_date) - INTERVAL '2 months'
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
LIMIT 15
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": "<",
        "value": -20,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Phân tích địa lý và peak hours — tối ưu marketing scheduling

# Phân tích địa lý và peak hours — tối ưu marketing scheduling

```json metabase-pos
{ "row": 28, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Revenue by Province (Top 10)

Top 10 provinces by revenue from shipping address.

```sql
SELECT
    g.province as "Province",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_geography g ON o.shipping_geography_key = g.geography_key
WHERE o.scope_sales
  AND o.is_active_order
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND o.ordered_at < date_trunc('month', current_date)
  AND g.province IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Province"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 29, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Order Heatmap — Day x Hour

Peak ordering windows for marketing scheduling.

```sql
SELECT
    CASE EXTRACT(DOW FROM ordered_at)
        WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
        WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri'
        WHEN 6 THEN 'Sat' END as "Day",
    EXTRACT(HOUR FROM ordered_at)::int as "Hour",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE scope_sales
  AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
  AND ordered_at < date_trunc('month', current_date)
GROUP BY 1, 2, EXTRACT(DOW FROM ordered_at)
ORDER BY EXTRACT(DOW FROM ordered_at), 2
```

```json metabase-viz
{
  "display": "pivot",
  "visualization_settings": {
    "table.pivot": true,
    "table.cell_column": "Orders",
    "pivot.show_column_totals": false,
    "pivot.show_row_totals": false,
    "table.column_formatting": [
      {
        "columns": ["Orders"],
        "type": "range",
        "colors": ["#FFFFFF", "#509EE3"],
        "min_type": "all",
        "max_type": "all"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 29, "col": 9, "size_x": 9, "size_y": 6 }
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
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```
<!-- text-id:trust-block -->

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_marketing_spend + fact_order_economics · **Cadence:** monthly · **Scope:** scope_retail · **Caveats:** ROAS attribution last-click
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: ROI & Margin


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

#### 📝 Text: Marketing P&L — ROAS, margin contribution và channel profit (Retail only, last-click attribution)

# Marketing P&L — ROAS, margin contribution và channel profit (Retail only, last-click attribution)

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: ROAS + Margin by Channel

ROAS and margin breakdown by channel for Retail scope. Attribution: last-click via channel_key match. CAC analysis pending (acquisition_source NULL).

```sql
WITH spend AS (
    SELECT
        channel_key,
        SUM(spend_amount) AS spend
    FROM fact_marketing_spend
    WHERE date_key >= CAST(strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%Y%m%d') AS INT)
      AND date_key <  CAST(strftime(date_trunc('month', current_date), '%Y%m%d') AS INT)
    GROUP BY channel_key
),
prev_spend AS (
    SELECT
        channel_key,
        SUM(spend_amount) AS spend
    FROM fact_marketing_spend
    WHERE date_key >= CAST(strftime(date_trunc('month', current_date) - INTERVAL '2 months', '%Y%m%d') AS INT)
      AND date_key <  CAST(strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%Y%m%d') AS INT)
    GROUP BY channel_key
),
perf AS (
    SELECT
        o.channel_key,
        SUM(o.net_revenue)        AS rev,
        SUM(o.gross_profit)       AS gross_profit,
        SUM(o.channel_net_profit) AS net_profit
    FROM fact_order_economics o
    WHERE o.date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND o.date_key <  CAST(strftime(date_trunc('month', current_date)::DATE, '%Y%m%d') AS INTEGER)
      AND o.scope_retail
      AND o.is_active_order
      AND o.has_cogs
    GROUP BY o.channel_key
),
prev_perf AS (
    SELECT
        o.channel_key,
        SUM(o.net_revenue) AS rev
    FROM fact_order_economics o
    WHERE o.date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '2 months')::DATE, '%Y%m%d') AS INTEGER)
      AND o.date_key <  CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND o.scope_retail
      AND o.is_active_order
    GROUP BY o.channel_key
)
SELECT
    ch.channel_name                                              AS "Channel",
    COALESCE(s.spend, 0)                                        AS "Spend",
    COALESCE(p.rev, 0)                                          AS "Attributed Revenue",
    ROUND(COALESCE(p.rev, 0) / NULLIF(s.spend, 0), 2)          AS "ROAS",
    ROUND(COALESCE(p.gross_profit, 0) * 100.0
          / NULLIF(p.rev, 0), 1)                               AS "Margin %",
    ROUND(COALESCE(p.rev, 0) / NULLIF(s.spend, 0)
          * COALESCE(p.gross_profit, 0) / NULLIF(p.rev, 0), 2) AS "Profitable ROAS",
    CASE
        WHEN COALESCE(ps.spend, 0) = 0 THEN NULL
        ELSE ROUND((COALESCE(s.spend, 0) - ps.spend) * 100.0 / ps.spend, 1)
    END                                                          AS "Spend MoM %"
FROM dim_channels ch
LEFT JOIN spend      s  ON ch.channel_key = s.channel_key
LEFT JOIN prev_spend ps ON ch.channel_key = ps.channel_key
LEFT JOIN perf       p  ON ch.channel_key = p.channel_key
LEFT JOIN prev_perf  pp ON ch.channel_key = pp.channel_key
WHERE s.spend IS NOT NULL OR p.rev IS NOT NULL
ORDER BY COALESCE(p.rev, 0) / NULLIF(s.spend, 0) DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Margin %"],
        "type": "single",
        "operator": ">=",
        "value": 30,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Margin %"],
        "type": "single",
        "operator": "<",
        "value": 10,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["ROAS"],
        "type": "single",
        "operator": ">=",
        "value": 3,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["ROAS"],
        "type": "single",
        "operator": "<",
        "value": 1,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Spend": { "number_style": "currency", "currency": "VND", "compact": true },
      "Attributed Revenue": { "number_style": "currency", "currency": "VND", "compact": true },
      "Margin %": { "suffix": "%" },
      "Spend MoM %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Xác định channel profit contribution — kênh nào đang profit, kênh nào đang drain budget?

# Xác định channel profit contribution — kênh nào đang profit, kênh nào đang drain budget?

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Profit Contribution vs Spend

Combo chart: bar = spend, line = net_profit by channel. Retail scope, last closed month vs prior month. Attribution: last-click via channel_key.

```sql
WITH spend_cur AS (
    SELECT
        channel_key,
        SUM(spend_amount) AS spend
    FROM fact_marketing_spend
    WHERE date_key >= CAST(strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%Y%m%d') AS INT)
      AND date_key <  CAST(strftime(date_trunc('month', current_date), '%Y%m%d') AS INT)
    GROUP BY channel_key
),
spend_prev AS (
    SELECT
        channel_key,
        SUM(spend_amount) AS spend
    FROM fact_marketing_spend
    WHERE date_key >= CAST(strftime(date_trunc('month', current_date) - INTERVAL '2 months', '%Y%m%d') AS INT)
      AND date_key <  CAST(strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%Y%m%d') AS INT)
    GROUP BY channel_key
),
profit_cur AS (
    SELECT
        o.channel_key,
        SUM(o.channel_net_profit) AS net_profit
    FROM fact_order_economics o
    WHERE o.date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND o.date_key <  CAST(strftime(date_trunc('month', current_date)::DATE, '%Y%m%d') AS INTEGER)
      AND o.scope_retail
      AND o.is_active_order
    GROUP BY o.channel_key
),
profit_prev AS (
    SELECT
        o.channel_key,
        SUM(o.channel_net_profit) AS net_profit
    FROM fact_order_economics o
    WHERE o.date_key >= CAST(strftime((date_trunc('month', current_date) - INTERVAL '2 months')::DATE, '%Y%m%d') AS INTEGER)
      AND o.date_key <  CAST(strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%Y%m%d') AS INTEGER)
      AND o.scope_retail
      AND o.is_active_order
    GROUP BY o.channel_key
)
SELECT
    ch.channel_name                     AS "Channel",
    COALESCE(sc.spend, 0)               AS "Spend (This Month)",
    COALESCE(sp.spend, 0)               AS "Spend (Prior Month)",
    COALESCE(pc.net_profit, 0)          AS "Net Profit (This Month)",
    COALESCE(pp.net_profit, 0)          AS "Net Profit (Prior Month)"
FROM dim_channels ch
LEFT JOIN spend_cur  sc ON ch.channel_key = sc.channel_key
LEFT JOIN spend_prev sp ON ch.channel_key = sp.channel_key
LEFT JOIN profit_cur pc ON ch.channel_key = pc.channel_key
LEFT JOIN profit_prev pp ON ch.channel_key = pp.channel_key
WHERE sc.spend IS NOT NULL OR pc.net_profit IS NOT NULL
ORDER BY COALESCE(pc.net_profit, 0) DESC
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Spend (This Month)", "Net Profit (This Month)"],
    "series_settings": {
      "Spend (This Month)": { "display": "bar", "color": "#509EE3" },
      "Net Profit (This Month)": { "display": "line", "color": "#84BB4C", "line.marker_enabled": true }
    },
    "graph.y_axis.auto_split": true,
    "column_settings": {
      "Spend (This Month)": { "number_style": "currency", "currency": "VND", "compact": true },
      "Spend (Prior Month)": { "number_style": "currency", "currency": "VND", "compact": true },
      "Net Profit (This Month)": { "number_style": "currency", "currency": "VND", "compact": true },
      "Net Profit (Prior Month)": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 7 }
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
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```
<!-- text-id:trust-block -->

#### 📝 Text: Source & Freshness

**Source:** fact_orders + fact_marketing_spend + fact_order_economics · **Cadence:** monthly · **Scope:** scope_retail · **Caveats:** ROAS attribution last-click
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```


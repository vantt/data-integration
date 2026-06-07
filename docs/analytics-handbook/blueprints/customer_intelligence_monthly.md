---
primary_scope: scope_sales
scope_indicator: "[Cross]"
layer: L3
uses_concepts:
  - scope_sales
  - scope_retail
  - net_revenue
  - orders_count
  - aov
  - retention_rate
  - customer_acquisition
---

# 📘 Blueprint: Customer Intelligence Monthly [Cross]

> **Target Collection:** `Marketing & Customers`
> **Design Spec:** `designs/customer_intelligence_monthly.md`
> **Role:** CEO, Marketing Manager, Sales Ops
> **Archetype:** Operational Cockpit (3 tabs)

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` · Layer L3 `[Cross]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales)
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`scope_retail`](../semantic/segments.md#scope_retail) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`orders_count`](../semantic/metrics.md#orders_count) · [`aov`](../semantic/metrics.md#aov) · [`retention_rate`](../semantic/metrics.md#retention_rate) · [`customer_acquisition`](../semantic/metrics.md#customer_acquisition)
## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

---

### 🖥️ Dashboard: Customer Intelligence Monthly [Cross]

**Description**: Monthly deep-dive — customer health scorecard, value concentration, segment dynamics, purchase behavior, channel effectiveness, and acquisition quality across 3 focused tabs.

---

### 📑 Tab: Overview & Health

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

#### 📝 Text: Boi canh mua vu + YoY Caveat

**Bối cảnh mùa vụ VN Retail** — ưu tiên YoY khi xem tháng có seasonal event: Tết (Jan cuối/Feb đầu); 9/9 · 10/10 · **11/11** · 12/12 Shopee Mega Sale; Black Friday cuối Nov. Nếu tháng có seasonal event → **ưu tiên YoY %, không trust MoM % standalone.** ⚠ **YoY Caveat:** Các heroes dùng `mart_customer_status_snapshot_monthly` (Total Customers, Active Customers, Total LTV, Repeat %) **chưa có YoY** vì mart hiện không tồn tại trong DB. YoY sẽ được thêm sau khi mart được build với >= 24 months data. Heroes từ `dim_customers` (New Customers) đã có YoY.

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 3 }
```

#### 📝 Text: Monitor customer base health — growth, activity, and retention pulse check

# Monitor customer base health — growth, activity, and retention pulse check

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total Customers

Total customers with at least one order, with MoM comparison.

```sql
-- Snapshot-driven MoM: count all customers present in each month-end snapshot.
-- current = last day of previous calendar month (most recent closed month)
-- prev    = last day of the month before that
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT COUNT(*) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
),
previous_period AS (
    SELECT COUNT(*) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
)
SELECT
    c.value AS "Total Customers",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Active Customers (30d)

Customers with at least one order in the last 30 days, with MoM comparison.

```sql
-- Snapshot-driven MoM: status = 'ACTIVE' (last order <= 30d before month-end).
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT COUNT(*) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
      AND s.status = 'ACTIVE'
),
previous_period AS (
    SELECT COUNT(*) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
      AND s.status = 'ACTIVE'
)
SELECT
    c.value AS "Active (30d)",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 6, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: New Customers (Last Month)

Customers acquired in the previous calendar month, with MoM + YoY comparison.

```sql
-- YoY added 2026-05-28; uses dim_customers (no snapshot mart dependency)
WITH current_period AS (
    SELECT COUNT(*) as value
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date) - INTERVAL '1 month'
      AND created_at < date_trunc('month', current_date)
),
previous_period AS (
    SELECT COUNT(*) as value
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date) - INTERVAL '2 months'
      AND created_at < date_trunc('month', current_date) - INTERVAL '1 month'
),
prior_year AS (
    SELECT COUNT(*) as value
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND created_at <  date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    c.value                                                                      AS "New Customers",
    p.value                                                                      AS "Prev Month",
    py.value                                                                     AS "Prev Year (same month)",
    CASE WHEN p.value = 0 THEN NULL
         ELSE ROUND((c.value - p.value) * 100.0 / p.value, 1) END               AS "MoM %",
    CASE WHEN py.value = 0 THEN NULL
         ELSE ROUND((c.value - py.value) * 100.0 / py.value, 1) END             AS "YoY %"
FROM current_period c, previous_period p, prior_year py
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 3 }
```

#### ❓ Question: One-Time Buyer Rate

Percentage of customers who only placed 1 order, with MoM comparison.

```sql
-- Snapshot-driven MoM: orders_to_date = 1 as-of each month-end snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT ROUND(
        COUNT(CASE WHEN orders_to_date = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
    ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
),
previous_period AS (
    SELECT ROUND(
        COUNT(CASE WHEN orders_to_date = 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
    ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
)
SELECT
    c.value AS "One-Time %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "One-Time %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Assess customer status distribution — identify at-risk concentration

# Assess customer status distribution — identify at-risk concentration

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Customer Status Distribution

Donut chart showing Active / At Risk / Churned split.

```sql
SELECT
    customer_status as "Status",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1
ORDER BY
    CASE customer_status
        WHEN 'Active' THEN 1
        WHEN 'At Risk' THEN 2
        WHEN 'Churned' THEN 3
        ELSE 4
    END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Status",
    "pie.metric": "Customers",
    "pie.colors": {
      "Active": "#84BB4C",
      "At Risk": "#F9D45C",
      "Churned": "#EF8C8C"
    },
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{"row": 13, "col":0, "size_x":6, "size_y":6}
```

#### ❓ Question: Customer Segment Distribution

Donut chart showing VALUE_VIP / GOLD / SILVER / BRONZE split.

```sql
SELECT
    value_group as "Segment",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1
ORDER BY
    CASE value_group
        WHEN 'VALUE_VIP' THEN 1
        WHEN 'VALUE_GOLD' THEN 2
        WHEN 'VALUE_BRONZE' THEN 3
    END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Segment",
    "pie.metric": "Customers",
    "pie.colors": {
      "VALUE_VIP": "#7172AD",
      "VALUE_GOLD": "#509EE3",
      "VALUE_SILVER": "#88BDE6",
      "VALUE_BRONZE": "#C2D2E9"
    },
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{"row": 13, "col":6, "size_x":6, "size_y":6}
```

#### ❓ Question: Revenue from Top 20% Customers

Revenue concentration — Pareto indicator.

```sql
WITH ranked AS (
    SELECT
        lifetime_value,
        NTILE(5) OVER (ORDER BY lifetime_value DESC) as quintile
    FROM dim_customers
    WHERE customer_id != 'Unknown'
      AND order_count > 0
)
SELECT
    ROUND(
        SUM(CASE WHEN quintile = 1 THEN lifetime_value ELSE 0 END) * 100.0
        / NULLIF(SUM(lifetime_value), 0), 1
    ) as "Top 20% Revenue Share %"
FROM ranked
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Top 20% Revenue Share %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{"row": 13, "col":12, "size_x":6, "size_y":6}
```

---

#### 📝 Text: Track growth dynamics — is acquisition outpacing churn?

# Track growth dynamics — is acquisition outpacing churn?

```json metabase-pos
{"row": 19, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Monthly Acquisition vs Churn (6M)

Net customer growth — combo chart with bars for volume, line for net growth.

```sql
WITH new_customers AS (
    SELECT
        date_trunc('month', created_at)::date as month,
        COUNT(*) as acquired
    FROM dim_customers
    WHERE created_at >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND created_at < date_trunc('month', current_date)
      AND customer_id != 'Unknown'
    GROUP BY 1
),
churned_customers AS (
    SELECT
        date_trunc('month', last_order_date + INTERVAL '90' DAY)::date as month,
        COUNT(*) as churned
    FROM dim_customers
    WHERE customer_status = 'Churned'
      AND (last_order_date + INTERVAL '90' DAY) >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND (last_order_date + INTERVAL '90' DAY) < date_trunc('month', current_date)
    GROUP BY 1
)
SELECT
    COALESCE(n.month, c.month) as "Month",
    COALESCE(n.acquired, 0) as "Acquired",
    COALESCE(c.churned, 0) as "Churned",
    COALESCE(n.acquired, 0) - COALESCE(c.churned, 0) as "Net Growth"
FROM new_customers n
FULL OUTER JOIN churned_customers c ON n.month = c.month
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Month"],
    "graph.metrics": ["Acquired", "Churned", "Net Growth"],
    "series_settings": {
      "Acquired": { "display": "bar", "color": "#84BB4C" },
      "Churned": { "display": "bar", "color": "#EF8C8C" },
      "Net Growth": { "display": "line", "color": "#509EE3", "line.interpolate": "cardinal" }
    },
    "graph.y_axis.title_text": "Customers",
    "graph.x_axis.title_text": ""
  }
}
```

```json metabase-pos
{"row": 20, "col":0, "size_x":18, "size_y":6}
```

---

#### 📝 Text: Review segment health scorecard — flag segments with high churn or low activity

# Review segment health scorecard — flag segments with high churn or low activity

```json metabase-pos
{"row": 26, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Customer Health Scorecard

Per-segment vitals with conditional formatting.

```sql
SELECT
    value_group as "Segment",
    COUNT(*) as "Customers",
    ROUND(COUNT(CASE WHEN customer_status = 'Active' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Active %",
    ROUND(COUNT(CASE WHEN customer_status = 'At Risk' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "At Risk %",
    ROUND(COUNT(CASE WHEN customer_status = 'Churned' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Churned %",
    ROUND(COUNT(CASE WHEN order_count > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as "Repeat %",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV",
    ROUND(AVG(order_count), 1) as "Avg Orders",
    ROUND(AVG(recency_days), 0) as "Avg Recency"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1
ORDER BY
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 WHEN 'VALUE_SILVER' THEN 3 ELSE 4 END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Active %"],
        "type": "single",
        "operator": ">=",
        "value": 50,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Churned %"],
        "type": "single",
        "operator": ">=",
        "value": 30,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["At Risk %"],
        "type": "single",
        "operator": ">=",
        "value": 25,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Avg LTV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Active %": { "suffix": "%" },
      "At Risk %": { "suffix": "%" },
      "Churned %": { "suffix": "%" },
      "Repeat %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{"row": 27, "col":0, "size_x":18, "size_y":5}
```

---


#### 📝 Text: Source & Freshness

**Source:** dim_customers + fact_orders · **Cadence:** monthly · **Scope:** scope_retail
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Value & Segmentation


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

#### 📝 Text: Analyze customer value — where is revenue concentrated?

# Analyze customer value — where is revenue concentrated?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total Customer LTV

Cumulative lifetime value with MoM comparison.

```sql
-- Snapshot-driven MoM: SUM(lifetime_value_to_date) for base in each snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT SUM(lifetime_value_to_date) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
),
previous_period AS (
    SELECT SUM(lifetime_value_to_date) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
)
SELECT
    c.value AS "Total LTV",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Total LTV": {
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
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### ❓ Question: Avg LTV per Customer

Average lifetime value with MoM comparison.

```sql
-- Snapshot-driven MoM: AVG(lifetime_value_to_date) for base in each snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT ROUND(AVG(lifetime_value_to_date), 0) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
),
previous_period AS (
    SELECT ROUND(AVG(lifetime_value_to_date), 0) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
)
SELECT
    c.value AS "Avg LTV",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg LTV": {
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
{ "row": 3, "col": 6, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Orders per Customer

Average order count with MoM comparison.

```sql
-- Snapshot-driven MoM: AVG(orders_to_date) for base in each snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT ROUND(AVG(orders_to_date), 1) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
),
previous_period AS (
    SELECT ROUND(AVG(orders_to_date), 1) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
)
SELECT
    c.value AS "Avg Orders",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Repeat Purchase Rate

Percentage of customers with more than 1 order, with MoM comparison.

```sql
-- Snapshot-driven MoM: orders_to_date > 1 as-of each month-end snapshot.
WITH month_ends AS (
    SELECT
        (date_trunc('month', current_date) - INTERVAL '1 day')::date AS current_month_end,
        (date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::date AS prev_month_end
),
current_period AS (
    SELECT ROUND(
        COUNT(CASE WHEN orders_to_date > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
    ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.current_month_end
),
previous_period AS (
    SELECT ROUND(
        COUNT(CASE WHEN orders_to_date > 1 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1
    ) AS value
    FROM mart_customer_status_snapshot_monthly s, month_ends m
    WHERE s.snapshot_month = m.prev_month_end
)
SELECT
    c.value AS "Repeat %",
    p.value AS "Prev Month"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Repeat %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Examine LTV distribution — identify value clusters and Pareto effect

# Examine LTV distribution — identify value clusters and Pareto effect

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Customer Value Distribution

Histogram of customer lifetime value — understand the shape of the base.

```sql
SELECT
    CASE
        WHEN lifetime_value = 0 THEN '0 (No Revenue)'
        WHEN lifetime_value < 500000 THEN '< 500K'
        WHEN lifetime_value < 1000000 THEN '500K - 1M'
        WHEN lifetime_value < 2000000 THEN '1M - 2M'
        WHEN lifetime_value < 5000000 THEN '2M - 5M'
        WHEN lifetime_value < 10000000 THEN '5M - 10M'
        ELSE '10M+'
    END as "LTV Range",
    COUNT(*) as "Customers",
    ROUND(
        COUNT(*) * 100.0 / NULLIF(
            (SELECT COUNT(*) FROM dim_customers WHERE customer_id != 'Unknown' AND order_count > 0), 0
        ), 1
    ) as "% of Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1
ORDER BY MIN(lifetime_value)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["LTV Range"],
    "graph.metrics": ["Customers"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Lifetime Value Range",
    "graph.y_axis.title_text": "Customer Count"
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Segment Revenue Share

Revenue contribution donut by customer segment.

```sql
SELECT
    value_group as "Segment",
    SUM(lifetime_value) as "Revenue"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1
ORDER BY
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 WHEN 'VALUE_SILVER' THEN 3 ELSE 4 END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Segment",
    "pie.metric": "Revenue",
    "pie.colors": {
      "VALUE_VIP": "#7172AD",
      "VALUE_GOLD": "#509EE3",
      "VALUE_SILVER": "#88BDE6",
      "VALUE_BRONZE": "#C2D2E9"
    },
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 7, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Track segment performance trends — spending trajectory by segment

# Track segment performance trends — spending trajectory by segment

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: AOV by Segment Trend (6M)

Average order value trend by segment over 6 months.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as "Month",
    cust.value_group as "Segment",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND cust.customer_id != 'Unknown'
  AND cust.order_count > 0
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Month"],
    "graph.metrics": ["AOV"],
    "graph.series_order_dimension": "Segment",
    "series_settings": {
      "VALUE_VIP": { "color": "#7172AD" },
      "VALUE_GOLD": { "color": "#509EE3" },
      "VALUE_SILVER": { "color": "#88BDE6" },
      "VALUE_BRONZE": { "color": "#C2D2E9" }
    },
    "graph.y_axis.title_text": "AOV (VND)",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "AOV": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Revenue by Segment Trend (6M)

Revenue composition by segment over time — stacked area.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as "Month",
    cust.value_group as "Segment",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_customers cust ON o.customer_key = cust.customer_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '6 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND cust.customer_id != 'Unknown'
  AND cust.order_count > 0
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Month", "Segment"],
    "graph.metrics": ["Revenue"],
    "series_settings": {
      "VALUE_VIP": { "color": "#7172AD" },
      "VALUE_GOLD": { "color": "#509EE3" },
      "VALUE_SILVER": { "color": "#88BDE6" },
      "VALUE_BRONZE": { "color": "#C2D2E9" }
    },
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 14, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Review segment detail — identify underperforming segments for action

# Review segment detail — identify underperforming segments for action

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Segment Revenue & Metrics Detail

Comprehensive metrics per segment with conditional formatting.

```sql
SELECT
    value_group as "Segment",
    COUNT(*) as "Customers",
    SUM(lifetime_value) as "Total Revenue",
    ROUND(
        SUM(lifetime_value) * 100.0 / NULLIF(
            (SELECT SUM(lifetime_value) FROM dim_customers WHERE customer_id != 'Unknown'), 0
        ), 1
    ) as "Revenue %",
    ROUND(AVG(lifetime_value), 0) as "Avg LTV",
    ROUND(AVG(order_count), 1) as "Avg Orders",
    ROUND(AVG(recency_days), 0) as "Avg Recency"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Revenue %"],
        "type": "range",
        "colors": ["#FFFFFF", "#509EE3"],
        "min_type": "all",
        "max_type": "all",
        "highlight_row": false
      },
      {
        "columns": ["Avg Recency"],
        "type": "single",
        "operator": ">=",
        "value": 60,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Total Revenue": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Avg LTV": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Revenue %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 18, "size_y": 5 }
```

---


#### 📝 Text: Source & Freshness

**Source:** dim_customers + fact_orders · **Cadence:** monthly · **Scope:** scope_retail
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Behavior & Insights


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

#### 📝 Text: Analyze purchase behavior — channel and product preferences by segment

# Analyze purchase behavior — channel and product preferences by segment

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Assess channel effectiveness — which channels serve which segments best?

# Assess channel effectiveness — which channels serve which segments best?

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Revenue by Segment

Which channels drive revenue for each segment — stacked bar (last 3 months).

```sql
SELECT
    ch.channel_name as "Channel",
    cust.value_group as "Segment",
    SUM(o.net_revenue) as "Revenue"
FROM fact_orders o
JOIN dim_customers cust ON o.customer_key = cust.customer_key
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE o.scope_sales
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND cust.customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY 1, 3 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Channel", "Segment"],
    "graph.metrics": ["Revenue"],
    "series_settings": {
      "VALUE_VIP": { "color": "#7172AD" },
      "VALUE_GOLD": { "color": "#509EE3" },
      "VALUE_SILVER": { "color": "#88BDE6" },
      "VALUE_BRONZE": { "color": "#C2D2E9" }
    },
    "graph.y_axis.title_text": "Revenue (VND)",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Compare product affinity — VIP vs first-time buyer preferences

# Compare product affinity — VIP vs first-time buyer preferences

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top 10 Products — VIP Customers

What VIP customers buy most — guide retention offers (last 3 months).

```sql
SELECT
    p.product_name as "Product",
    SUM(s.net_revenue) as "Revenue"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
JOIN dim_customers cust ON o.customer_key = cust.customer_key
JOIN dim_products p ON s.product_key = p.product_key
WHERE cust.value_group = 'VALUE_VIP'
  AND o.scope_sales
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.ordered_at < date_trunc('month', current_date)
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Product"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#7172AD"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 10 Products — First-Time Buyers

Entry products for new customers — guide acquisition funnels (last 3 months).

```sql
SELECT
    p.product_name as "Product",
    SUM(s.net_revenue) as "Revenue"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
JOIN dim_customers cust ON o.customer_key = cust.customer_key
JOIN dim_products p ON s.product_key = p.product_key
WHERE date_trunc('month', o.ordered_at) = date_trunc('month', cust.first_order_date)
  AND o.scope_sales
  AND o.ordered_at >= date_trunc('month', current_date) - INTERVAL '3 months'
  AND o.ordered_at < date_trunc('month', current_date)
  AND cust.customer_id != 'Unknown'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Product"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 11, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Evaluate new customer quality — are acquisition cohorts improving?

# Evaluate new customer quality — are acquisition cohorts improving?

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: New Customer Quality Trend (6M)

Cohort quality: new customer volume + first-order AOV + 30-day repeat rate.

```sql
WITH first_orders AS (
    SELECT
        date_trunc('month', c.first_order_date)::date as cohort_month,
        c.customer_key,
        o.net_revenue as first_order_value
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_key = o.customer_key
        AND date_trunc('month', o.ordered_at) = date_trunc('month', c.first_order_date)
    WHERE c.first_order_date >= date_trunc('month', current_date) - INTERVAL '6 months'
      AND c.first_order_date < date_trunc('month', current_date)
      AND c.customer_id != 'Unknown'
      AND o.scope_sales
),
repeat_30d AS (
    SELECT DISTINCT
        fo.cohort_month,
        fo.customer_key
    FROM first_orders fo
    JOIN fact_orders o2 ON fo.customer_key = o2.customer_key
        AND o2.ordered_at > (SELECT MIN(first_order_date) FROM dim_customers WHERE customer_key = fo.customer_key)
        AND o2.ordered_at <= (SELECT MIN(first_order_date) + INTERVAL '30 days' FROM dim_customers WHERE customer_key = fo.customer_key)
        AND o2.scope_sales
)
SELECT
    fo.cohort_month as "Month",
    COUNT(DISTINCT fo.customer_key) as "New Customers",
    ROUND(AVG(fo.first_order_value), 0) as "Avg First Order",
    ROUND(
        COUNT(DISTINCT r.customer_key) * 100.0 / NULLIF(COUNT(DISTINCT fo.customer_key), 0), 1
    ) as "30d Repeat %"
FROM first_orders fo
LEFT JOIN repeat_30d r ON fo.customer_key = r.customer_key AND fo.cohort_month = r.cohort_month
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Month"],
    "graph.metrics": ["New Customers", "Avg First Order", "30d Repeat %"],
    "series_settings": {
      "New Customers": { "display": "bar", "color": "#509EE3" },
      "Avg First Order": { "display": "line", "color": "#7172AD", "line.interpolate": "cardinal" },
      "30d Repeat %": { "display": "line", "color": "#F9D45C", "line.interpolate": "cardinal" }
    },
    "graph.y_axis.title_text": "",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "Avg First Order": { "number_style": "currency", "currency": "VND", "compact": true },
      "30d Repeat %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Review demographics and loyalty — targeting and engagement signals

# Review demographics and loyalty — targeting and engagement signals

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Loyalty Point Distribution by Segment

Loyalty engagement levels per segment — bar chart.

```sql
SELECT
    value_group as "Segment",
    COUNT(CASE WHEN loyalty_points = 0 THEN 1 END) as "0 Points",
    COUNT(CASE WHEN loyalty_points BETWEEN 1 AND 999 THEN 1 END) as "1-999",
    COUNT(CASE WHEN loyalty_points BETWEEN 1000 AND 4999 THEN 1 END) as "1K-5K",
    COUNT(CASE WHEN loyalty_points >= 5000 THEN 1 END) as "5K+"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1
ORDER BY
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 WHEN 'VALUE_SILVER' THEN 3 ELSE 4 END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Segment"],
    "graph.metrics": ["0 Points", "1-999", "1K-5K", "5K+"],
    "graph.colors": ["#C2D2E9", "#88BDE6", "#509EE3", "#7172AD"],
    "graph.y_axis.title_text": "Customers",
    "graph.x_axis.title_text": ""
  }
}
```

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Gender Distribution by Segment

Demographic breakdown for marketing persona targeting.

```sql
SELECT
    value_group as "Segment",
    COALESCE(NULLIF(gender, ''), 'Unknown') as "Gender",
    COUNT(*) as "Customers"
FROM dim_customers
WHERE customer_id != 'Unknown'
  AND order_count > 0
GROUP BY 1, 2
ORDER BY
    CASE value_group WHEN 'VALUE_VIP' THEN 1 WHEN 'VALUE_GOLD' THEN 2 WHEN 'VALUE_SILVER' THEN 3 ELSE 4 END,
    3 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Segment", "Gender"],
    "graph.metrics": ["Customers"],
    "graph.colors": ["#509EE3", "#F2A86F", "#A989C5"],
    "graph.y_axis.title_text": "Customers",
    "graph.x_axis.title_text": ""
  }
}
```

```json metabase-pos
{ "row": 25, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: P3 Behavioral metrics — discount sensitivity and purchase cycle by segment

# P3 Behavioral metrics — discount sensitivity and purchase cycle by segment

```json metabase-pos
{ "row": 31, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Sensitivity Distribution

Share of retail customers by `discount_sensitivity` label — understand promo dependency vs full-price buying behavior.

```sql
SELECT
    COALESCE(discount_sensitivity, 'Unknown / Insufficient data') AS "Discount Sensitivity",
    COUNT(*) AS "Customers",
    ROUND(COUNT(*) * 100.0 / NULLIF(
        (SELECT COUNT(*) FROM dim_customers WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER') AND customer_id != 'Unknown'), 0
    ), 1) AS "% of Base"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
GROUP BY 1
ORDER BY
    CASE discount_sensitivity
        WHEN 'PROMO_DEPENDENT' THEN 1
        WHEN 'PROMO_MIXED'     THEN 2
        WHEN 'FULL_PRICE'      THEN 3
        ELSE 4
    END
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Discount Sensitivity",
    "pie.metric": "Customers",
    "pie.colors": {
      "PROMO_DEPENDENT":              "#EF8C8C",
      "PROMO_MIXED":                  "#F9D45C",
      "FULL_PRICE":                   "#84BB4C",
      "Unknown / Insufficient data":  "#C2D2E9"
    },
    "pie.show_legend": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 32, "col": 0, "size_x": 6, "size_y": 6 }
```

#### ❓ Question: Discount Sensitivity by Segment

Cross-tab: how promo dependency is distributed within each value tier — stacked bar.

```sql
SELECT
    value_group AS "Segment",
    COALESCE(discount_sensitivity, 'Unknown') AS "Discount Sensitivity",
    COUNT(*) AS "Customers"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
GROUP BY 1, 2
ORDER BY
    CASE value_group
        WHEN 'VALUE_VIP'    THEN 1
        WHEN 'VALUE_GOLD'   THEN 2
        WHEN 'VALUE_SILVER' THEN 3
        ELSE 4
    END,
    CASE discount_sensitivity
        WHEN 'PROMO_DEPENDENT' THEN 1
        WHEN 'PROMO_MIXED'     THEN 2
        WHEN 'FULL_PRICE'      THEN 3
        ELSE 4
    END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "normalized",
    "graph.dimensions": ["Segment", "Discount Sensitivity"],
    "graph.metrics": ["Customers"],
    "series_settings": {
      "PROMO_DEPENDENT": { "color": "#EF8C8C" },
      "PROMO_MIXED":     { "color": "#F9D45C" },
      "FULL_PRICE":      { "color": "#84BB4C" },
      "Unknown":         { "color": "#C2D2E9" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "% of Segment"
  }
}
```

```json metabase-pos
{ "row": 32, "col": 6, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Avg Days Between Orders by Segment

Purchase cycle length per value tier — informs optimal re-engagement timing for each segment.

```sql
SELECT
    value_group AS "Segment",
    COUNT(CASE WHEN avg_days_between_orders IS NOT NULL THEN 1 END) AS "Repeat Customers",
    ROUND(AVG(avg_days_between_orders), 0) AS "Avg Days Between Orders",
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_days_between_orders), 0) AS "Median Days",
    ROUND(MIN(avg_days_between_orders), 0) AS "Min Days",
    ROUND(MAX(avg_days_between_orders), 0) AS "Max Days"
FROM dim_customers
WHERE customer_type NOT IN ('WHOLESALE', 'PARTNER', 'STAFF', 'KOL', 'CROSSBORDER')
  AND customer_id != 'Unknown'
  AND avg_days_between_orders IS NOT NULL
GROUP BY 1
ORDER BY
    CASE value_group
        WHEN 'VALUE_VIP'    THEN 1
        WHEN 'VALUE_GOLD'   THEN 2
        WHEN 'VALUE_SILVER' THEN 3
        ELSE 4
    END
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Avg Days Between Orders": { "suffix": " days" },
      "Median Days":             { "suffix": " days" },
      "Min Days":                { "suffix": " days" },
      "Max Days":                { "suffix": " days" }
    },
    "table.column_formatting": [
      {
        "columns": ["Avg Days Between Orders"],
        "type": "range",
        "colors": ["#84BB4C", "#F9D45C", "#EF8C8C"],
        "min_type": "custom",
        "min_value": 0,
        "max_type": "custom",
        "max_value": 90
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 38, "col": 0, "size_x": 18, "size_y": 5 }
```

#### 📝 Text: Source & Freshness

**Source:** dim_customers + fact_orders · **Cadence:** monthly · **Scope:** scope_retail
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


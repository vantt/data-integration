---
primary_scope: scope_sales
scope_indicator: "[Cross]"
layer: L1.5
uses_concepts: [scope_sales, filter_has_cogs, net_revenue, gross_profit, cogs_amount]
merged_from: [product_profitability.md (#36), finance_product_cost_margin.md (#76)]
---

# Product Profitability & Cost [Cross] Blueprint

Merged from:
- **#36 Product Profitability [All]** — margin ranking, cross-channel breakdown
- **#76 Product Cost-to-Margin Heatmap [Cross]** — COGS variance alerts, scatter, margin distribution

Audience: Merchandising + Finance. Cadence: rolling-30d / monthly. Scope: `has_cogs = true` (~42 SKU).

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` + `filter_has_cogs` · Layer L1.5 `[Cross]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales) · [`segments.md#filter_has_cogs`](../semantic/segments.md#filter_has_cogs)
> **Why:** Product profitability covers all segments for true SKU margin view. `has_cogs = true` required.
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`filter_has_cogs`](../semantic/segments.md#filter_has_cogs) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`gross_profit`](../semantic/metrics.md#gross_profit) · [`cogs_amount`](../semantic/metrics.md#cogs_amount)

All margin queries: `WHERE NOT is_promo_line AND revenue_net_of_discount > 0`.

## 📂 Collection: Merchandising & Product

### Dashboard: Product Profitability & Cost [Cross]

**Description**: SKU margin ranking + COGS variance anomalies — sản phẩm nào tạo/mất margin, bất thường giá vốn. Audience: Merchandising + Finance. 2 tabs: Margin Ranking + Cost & Variance.

> **Database:** Sapo

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past30days",
  "field_id": 324
}
```

#### Filter: Channel

```json metabase-filter
{
  "slug": "channel",
  "type": "string/=",
  "field_id": 349
}
```

---

### Tab: Margin Ranking

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
    '📅 Dữ liệu tháng: ' || strftime(snapshot_month, '%m/%Y') AS "Chu kỳ báo cáo"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
LIMIT 1
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

---

#### 📝 Text: Coverage Note

⚠️ **Phạm vi COGS:** Margin tính từ `mart_sku_economics_monthly` (H010-corrected) cho ~42 SKU has_cogs. Số liệu là tháng gần nhất trong mart (không lọc theo date_range filter). SKU chưa khớp MISA không có margin.

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### 📝 Text: Hero KPIs

## Tổng quan — margin và COGS trong kỳ

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total SKUs with COGS

```sql
SELECT COUNT(DISTINCT product_code) AS "SKU có COGS"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Margin %

```sql
SELECT
    ROUND(
        SUM(realized_gross_profit) * 100.0 / NULLIF(SUM(net_revenue), 0),
        1
    ) AS "Avg Margin %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg Margin %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 4, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Margin Outlier Count

Số SKU có realized margin < 10%.

```sql
SELECT COUNT(*) AS "SKU margin thap (< 10%)"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND realized_margin_pct < 10
  AND net_revenue > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 4, "col": 8, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Highest Margin Product

```sql
SELECT
    product_name AS "San pham",
    ROUND(realized_margin_pct, 1) AS "Margin %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
  AND order_count >= 3
ORDER BY realized_margin_pct DESC
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "San pham"
  }
}
```

```json metabase-pos
{ "row": 4, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Lowest Margin Product

```sql
SELECT
    product_name AS "San pham",
    ROUND(realized_margin_pct, 1) AS "Margin %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
  AND order_count >= 3
ORDER BY realized_margin_pct ASC
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "San pham"
  }
}
```

```json metabase-pos
{ "row": 4, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### 📝 Text: Ranking Heading

## Top/Bottom 20 sản phẩm theo lãi gộp và margin %

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top Products by Profit

Horizontal bar — top 20 sản phẩm đóng góp lãi gộp nhiều nhất.

```sql
SELECT
    product_name AS "San pham",
    realized_gross_profit AS "Lai gop"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
ORDER BY realized_gross_profit DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["Lai gop"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Lai gop (VND)",
    "graph.y_axis.title_text": "",
    "column_settings": {
      "Lai gop": {
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
{ "row": 8, "col": 0, "size_x": 9, "size_y": 9 }
```

#### ❓ Question: Bottom Margin Products

Horizontal bar — 20 sản phẩm margin thấp nhất.

```sql
SELECT
    product_name AS "San pham",
    ROUND(realized_margin_pct, 1) AS "Gross Margin %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
  AND order_count >= 2
ORDER BY realized_margin_pct ASC
LIMIT 20
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["Gross Margin %"],
    "graph.colors": ["#EF8C8C"],
    "graph.x_axis.title_text": "Gross Margin (%)",
    "graph.y_axis.title_text": "",
    "table.column_formatting": [
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 25,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 9, "size_x": 9, "size_y": 9 }
```

---

#### 📝 Text: Cross-Channel Heading

## SKU margin breakdown theo kênh (cross-channel)

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: SKU Margin by Channel

Top 20 SKU — corrected realized margin % with dominant channel. Channel grain is the SKU's top revenue channel (from mart). Cross-channel breakdown not available with H010-corrected COGS.

```sql
-- Uses mart_sku_economics_monthly: realized_margin_pct is H010-corrected.
-- top_channel_name = dominant channel by revenue for this SKU in the snapshot month.
SELECT
    product_name                                AS "SKU",
    COALESCE(top_channel_name, 'Khac')          AS "Kenh chinh",
    net_revenue                                 AS "Doanh thu",
    ROUND(realized_margin_pct, 1)               AS "Gross Margin %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
ORDER BY net_revenue DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["SKU", "Kenh chinh"],
    "graph.metrics": ["Gross Margin %"],
    "stackable.stack_type": null,
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Gross Margin %",
    "column_settings": {
      "Gross Margin %": { "suffix": "%", "decimals": 1 },
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### 📝 Text: Detail Table Heading

## Chi tiết sản phẩm — margin, doanh thu, giá vốn theo kênh

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Product Detail Table

Full product breakdown with conditional formatting. Channel grain not available with H010-corrected COGS; shows SKU-level corrected margin.

```sql
SELECT
    product_name                        AS "San pham",
    COALESCE(top_channel_name, 'Khac') AS "Kenh chinh",
    units_sold                          AS "SL",
    net_revenue                         AS "Doanh thu",
    cogs_amount                         AS "Gia von",
    realized_gross_profit               AS "Lai gop",
    ROUND(realized_margin_pct, 1)       AS "Gross Margin %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
ORDER BY realized_gross_profit DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "table.column_formatting": [
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 25,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": ">=",
        "value": 50,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Gia von": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Lai gop": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Source & Freshness Tab1

**Source:** mart_sku_economics_monthly (H010-corrected realized_margin_pct) · **Cadence:** monthly snapshot · **Scope:** latest snapshot_month · **Coverage:** ~42 SKU has_cogs · **Note:** date_range / channel filters removed — mart is monthly aggregated; use COGS Variance tab for period drill-down
<!-- text-id:source-freshness-tab1 -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### Tab: Cost & Variance

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
    '📅 Dữ liệu tháng: ' || strftime(snapshot_month, '%m/%Y') AS "Chu kỳ báo cáo"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
LIMIT 1
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

---

#### 📝 Text: Cost Hero KPIs

## COGS alerts — giá vốn bất thường trong kỳ

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total SKUs Sold

```sql
SELECT COUNT(DISTINCT product_code) AS "Tong SKU"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Avg Margin % (Cost Tab)

```sql
SELECT
    ROUND(
        SUM(realized_gross_profit) * 100.0 / NULLIF(SUM(net_revenue), 0),
        1
    ) AS "Avg Margin %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg Margin %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 4, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: COGS Variance Alert Count

Số SKU có COGS/unit lệch > 10% so với trung bình 3 tháng trước.

```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date)::DATE AS p_start, MAX(posting_date)::DATE AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND quantity > 0
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
current_cogs AS (
    SELECT
        product_code,
        SUM(cogs_amount) / NULLIF(SUM(quantity), 0) AS cogs_per_unit_current
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND quantity > 0
      AND posting_date >= filter_bounds.p_start
      AND posting_date <= filter_bounds.p_end
      [[AND {{channel}}]]
    GROUP BY product_code
),
avg_3m AS (
    SELECT
        product_code,
        SUM(cogs_amount) / NULLIF(SUM(quantity), 0) AS cogs_per_unit_3m_avg
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND quantity > 0
      AND posting_date >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND posting_date <  filter_bounds.p_start
      [[AND {{channel}}]]
    GROUP BY product_code
)
SELECT COUNT(*) AS "SKU COGS spike (> 10%)"
FROM current_cogs c
JOIN avg_3m a USING (product_code)
WHERE ABS(
    (c.cogs_per_unit_current - a.cogs_per_unit_3m_avg)
    / NULLIF(a.cogs_per_unit_3m_avg, 0)
) > 0.10
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 8, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Scatter Section

SKU Margin vs Revenue — mỗi điểm là 1 SKU (30 ngày gần nhất)

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: SKU Margin vs Revenue Scatter

Scatter: X = doanh thu, Y = corrected margin %, kích thước = số đơn. Latest snapshot month.

```sql
SELECT
    product_name                                AS "SKU",
    COALESCE(top_channel_name, 'Khac')          AS "Kenh",
    net_revenue                                 AS "Doanh thu",
    ROUND(realized_margin_pct, 1)               AS "Gross Margin %",
    order_count                                 AS "So don"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
ORDER BY net_revenue DESC
LIMIT 200
```

```json metabase-viz
{
  "display": "scatter",
  "visualization_settings": {
    "graph.dimensions": ["Doanh thu"],
    "graph.metrics": ["Gross Margin %"],
    "scatter.bubble": "So don",
    "graph.x_axis.title_text": "Doanh thu (VND)",
    "graph.y_axis.title_text": "Gross Margin %",
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Gross Margin %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### 📝 Text: Top 50 SKU Table

Top 50 SKU — doanh thu, giá vốn, margin, COGS variance

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top 50 SKU Detail Table

Table: SKU × Revenue × COGS × Corrected Margin % × COGS variance vs 3-month avg. Conditional formatting.

```sql
-- realized_margin_pct is H010-corrected. COGS variance pre-computed from mart.
SELECT
    product_name                        AS "SKU",
    net_revenue                         AS "Doanh thu",
    cogs_amount                         AS "Gia von",
    ROUND(realized_margin_pct, 1)       AS "Gross Margin %",
    ROUND(cogs_per_unit, 0)             AS "COGS/don vi",
    ROUND(cogs_per_unit_3m_avg, 0)      AS "COGS avg 3M",
    ROUND(cogs_variance_pct, 1)         AS "COGS variance %"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
ORDER BY net_revenue DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Gia von":   { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "COGS/don vi": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "COGS avg 3M": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Gross Margin %":   { "suffix": "%", "decimals": 1 },
      "COGS variance %":  { "suffix": "%", "decimals": 1 }
    },
    "table.column_formatting": [
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 10,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": ">=",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["COGS variance %"],
        "type": "single",
        "operator": ">",
        "value": 10,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["COGS variance %"],
        "type": "single",
        "operator": "<",
        "value": -10,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Margin Distribution

Phân phối margin — bao nhiêu SKU ở từng nhóm?

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 9, "size_y": 1 }
```

#### ❓ Question: Margin Distribution Histogram

Phân phối SKU theo nhóm realized margin — chia bucket 10%.

```sql
SELECT
    CASE
        WHEN realized_margin_pct < 0    THEN '< 0% (lo)'
        WHEN realized_margin_pct < 10   THEN '0–10% (alert)'
        WHEN realized_margin_pct < 20   THEN '10–20%'
        WHEN realized_margin_pct < 30   THEN '20–30%'
        WHEN realized_margin_pct < 40   THEN '30–40%'
        WHEN realized_margin_pct < 50   THEN '40–50%'
        WHEN realized_margin_pct < 60   THEN '50–60%'
        ELSE                                 '> 60% (star)'
    END AS "Nhom margin",
    COUNT(*) AS "So SKU"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND net_revenue > 0
GROUP BY 1
ORDER BY MIN(realized_margin_pct)
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Nhom margin"],
    "graph.metrics": ["So SKU"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Margin bucket",
    "graph.y_axis.title_text": "So luong SKU"
  }
}
```

```json metabase-pos
{ "row": 27, "col": 0, "size_x": 9, "size_y": 7 }
```

---

#### 📝 Text: COGS Variance Alert

COGS spike alert — SKU COGS tháng này vs trung bình 3 tháng > 10%

```json metabase-pos
{ "row": 26, "col": 9, "size_x": 9, "size_y": 1 }
```

#### ❓ Question: COGS Variance Alert Table

Top SKU theo độ lệch COGS/đơn vị so với trung bình 3 tháng (cogs_variance_pct). Hiển thị top movers — không lọc cứng theo ngưỡng nên bảng luôn có dữ liệu; khi COGS ổn định (hiện tại đều <1%) vẫn thấy SKU biến động nhất.

```sql
-- Pre-computed cogs_variance_pct from mart_sku_economics_monthly (latest month). DRY + robust:
-- avoids the empty-prior-window bug of re-deriving variance, and never returns 0 rows.
SELECT
    product_name                   AS "SKU",
    ROUND(cogs_per_unit, 0)        AS "COGS thang nay",
    ROUND(cogs_per_unit_3m_avg, 0) AS "COGS avg 3M",
    ROUND(cogs_variance_pct, 1)    AS "Variance %",
    order_count                    AS "So don"
FROM mart_sku_economics_monthly
WHERE snapshot_month = (SELECT MAX(snapshot_month) FROM mart_sku_economics_monthly)
  AND cogs_variance_pct IS NOT NULL
ORDER BY ABS(cogs_variance_pct) DESC
LIMIT 30
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "column_settings": {
      "COGS thang nay": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "COGS avg 3M":    { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "Variance %":     { "suffix": "%", "decimals": 1 }
    },
    "table.column_formatting": [
      {
        "columns": ["Variance %"],
        "type": "single",
        "operator": ">",
        "value": 10,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Variance %"],
        "type": "single",
        "operator": "<",
        "value": -10,
        "color": "#84BB4C",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 27, "col": 9, "size_x": 9, "size_y": 7 }
```

---

#### 📝 Text: Source & Freshness Tab2

**Source:** mart_sku_economics_monthly (margin cards H010-corrected) + int_misa_sales_lines (COGS Variance Alert detail) · **Cadence:** monthly snapshot · **Caveats:** scatter/histogram use latest snapshot month only; COGS Variance Alert Table uses mart pre-computed variance
<!-- text-id:source-freshness-tab2 -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

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
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND revenue_net_of_discount > 0
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
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
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER) * 12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start, '%d/%m/%Y') || ' – ' || strftime(p_end, '%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur <= 6
                  THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR || ' months')::INTERVAL)::DATE
             END, '%d/%m/%Y') || ' – ' ||
    strftime((p_start - 1)::DATE, '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

---

#### 📝 Text: Coverage Note

⚠️ **Phạm vi COGS:** Margin chỉ tính cho ~42 SKU đã khớp với sổ MISA (has_cogs). SKU chưa khớp có doanh thu nhưng không có cột margin.

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
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
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
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Avg Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
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

Số SKU có gross margin < 10%.

```sql
SELECT COUNT(*) AS "SKU margin thap (< 10%)"
FROM (
    SELECT
        product_code,
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) AS margin_pct
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND revenue_net_of_discount > 0
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
    GROUP BY product_code
    HAVING SUM(revenue_net_of_discount) > 0
) t
WHERE margin_pct < 10
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
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name
HAVING COUNT(*) >= 3
ORDER BY "Margin %" DESC
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
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name
HAVING COUNT(*) >= 3
ORDER BY "Margin %" ASC
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
    SUM(gross_profit) AS "Lai gop"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name
ORDER BY "Lai gop" DESC
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
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Gross Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name
HAVING COUNT(*) >= 2
ORDER BY "Gross Margin %" ASC
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

Top 20 SKU — margin % per channel (cross-channel comparison).

```sql
WITH top_skus AS (
    SELECT product_code
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND revenue_net_of_discount > 0
      [[AND {{date_range}}]]
    GROUP BY product_code
    ORDER BY SUM(revenue_net_of_discount) DESC
    LIMIT 20
)
SELECT
    product_name                                                                AS "SKU",
    COALESCE(channel_name, 'Khac')                                             AS "Kenh",
    SUM(revenue_net_of_discount)                                               AS "Doanh thu",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    )                                                                           AS "Gross Margin %"
FROM int_misa_sales_lines
WHERE product_code IN (SELECT product_code FROM top_skus)
  AND NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name, channel_name
ORDER BY SUM(revenue_net_of_discount) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["SKU", "Kenh"],
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

Full product breakdown with conditional formatting.

```sql
SELECT
    product_name AS "San pham",
    channel_name AS "Kenh",
    SUM(quantity) AS "SL",
    SUM(revenue_net_of_discount) AS "Doanh thu",
    SUM(cogs_amount) AS "Gia von",
    SUM(gross_profit) AS "Lai gop",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Gross Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name, channel_name
ORDER BY "Lai gop" DESC
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

**Source:** int_misa_sales_lines · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line · **Coverage:** margin chỉ cho SKU có COGS (has_cogs ~42 SKU)
<!-- text-id:source-freshness-tab1 -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### Tab: Cost & Variance

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date)::DATE AS p_start, MAX(posting_date)::DATE AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND revenue_net_of_discount > 0
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
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

---

#### 📝 Text: Cost Hero KPIs

## COGS alerts — giá vốn bất thường trong kỳ

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total SKUs Sold

```sql
SELECT COUNT(DISTINCT product_code) AS "Tong SKU"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
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
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Avg Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
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

Scatter: X = doanh thu, Y = margin %, kích thước = số đơn. Last 30 days.

```sql
SELECT
    product_name                                                                    AS "SKU",
    COALESCE(channel_name, 'Khac')                                                  AS "Kenh",
    SUM(revenue_net_of_discount)                                                    AS "Doanh thu",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    )                                                                               AS "Gross Margin %",
    COUNT(DISTINCT voucher_no)                                                      AS "So don"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  AND posting_date >= current_date - INTERVAL '30 days'
  [[AND {{channel}}]]
GROUP BY product_name, channel_name
HAVING SUM(revenue_net_of_discount) > 0
ORDER BY "Doanh thu" DESC
LIMIT 200
```

```json metabase-viz
{
  "display": "scatter",
  "visualization_settings": {
    "graph.dimensions": ["Doanh thu", "Gross Margin %"],
    "graph.metrics": ["So don"],
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

Table: SKU × Revenue × COGS × Margin % × COGS variance vs 3-month avg. Conditional formatting.

```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date)::DATE AS p_start, MAX(posting_date)::DATE AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND revenue_net_of_discount > 0
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
current_period AS (
    SELECT
        product_code,
        product_name,
        SUM(revenue_net_of_discount)                                                    AS revenue,
        SUM(cogs_amount)                                                                AS cogs_total,
        SUM(gross_profit)                                                               AS gross_profit,
        SUM(quantity)                                                                   AS qty,
        SUM(cogs_amount) / NULLIF(SUM(quantity), 0)                                    AS cogs_per_unit_current
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND revenue_net_of_discount > 0
      AND posting_date >= filter_bounds.p_start
      AND posting_date <= filter_bounds.p_end
      [[AND {{channel}}]]
    GROUP BY product_code, product_name
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
SELECT
    cp.product_name                                                                      AS "SKU",
    cp.revenue                                                                           AS "Doanh thu",
    cp.cogs_total                                                                        AS "Gia von",
    ROUND(cp.gross_profit * 100.0 / NULLIF(cp.revenue, 0), 1)                          AS "Gross Margin %",
    ROUND(cp.cogs_per_unit_current, 0)                                                   AS "COGS/don vi",
    ROUND(a.cogs_per_unit_3m_avg, 0)                                                     AS "COGS avg 3M",
    ROUND(
        (cp.cogs_per_unit_current - a.cogs_per_unit_3m_avg)
        * 100.0 / NULLIF(a.cogs_per_unit_3m_avg, 0),
        1
    )                                                                                    AS "COGS variance %"
FROM current_period cp
LEFT JOIN avg_3m a USING (product_code)
ORDER BY cp.revenue DESC
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

Phân phối SKU theo nhóm margin — chia bucket 10%.

```sql
SELECT
    CASE
        WHEN margin_pct < 0    THEN '< 0% (lo)'
        WHEN margin_pct < 10   THEN '0–10% (alert)'
        WHEN margin_pct < 20   THEN '10–20%'
        WHEN margin_pct < 30   THEN '20–30%'
        WHEN margin_pct < 40   THEN '30–40%'
        WHEN margin_pct < 50   THEN '40–50%'
        WHEN margin_pct < 60   THEN '50–60%'
        ELSE                        '> 60% (star)'
    END AS "Nhom margin",
    COUNT(*) AS "So SKU"
FROM (
    SELECT
        product_code,
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) AS margin_pct
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND revenue_net_of_discount > 0
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
    GROUP BY product_code
) t
GROUP BY 1
ORDER BY MIN(margin_pct)
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

SKU có COGS/unit lệch > 10% so với avg 3 tháng — sorted by absolute variance desc.

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
        product_name,
        SUM(cogs_amount) / NULLIF(SUM(quantity), 0) AS cogs_per_unit_current,
        COUNT(DISTINCT voucher_no)                   AS don_count
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND quantity > 0
      AND posting_date >= filter_bounds.p_start
      AND posting_date <= filter_bounds.p_end
      [[AND {{channel}}]]
    GROUP BY product_code, product_name
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
SELECT
    c.product_name                                                              AS "SKU",
    ROUND(c.cogs_per_unit_current, 0)                                          AS "COGS thang nay",
    ROUND(a.cogs_per_unit_3m_avg, 0)                                           AS "COGS avg 3M",
    ROUND(
        (c.cogs_per_unit_current - a.cogs_per_unit_3m_avg)
        * 100.0 / NULLIF(a.cogs_per_unit_3m_avg, 0),
        1
    )                                                                           AS "Variance %",
    c.don_count                                                                 AS "So don"
FROM current_cogs c
JOIN avg_3m a USING (product_code)
WHERE ABS(
    (c.cogs_per_unit_current - a.cogs_per_unit_3m_avg)
    / NULLIF(a.cogs_per_unit_3m_avg, 0)
) > 0.10
ORDER BY ABS(
    (c.cogs_per_unit_current - a.cogs_per_unit_3m_avg)
    / NULLIF(COALESCE(a.cogs_per_unit_3m_avg, 1), 0)
) DESC
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

**Source:** int_misa_sales_lines · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line · **Caveats:** COGS variance requires prior-period data; may show 0 alerts if new SKU
<!-- text-id:source-freshness-tab2 -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

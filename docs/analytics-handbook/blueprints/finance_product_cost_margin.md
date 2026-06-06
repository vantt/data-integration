---
primary_scope: scope_sales
scope_indicator: "[All]"
layer: L1.5
uses_concepts: [scope_sales, filter_has_cogs, cogs_amount, gross_profit, net_revenue]
---

# Blueprint: Product Cost-to-Margin Heatmap [Cross]

**Playbook**: [Product Cost-to-Margin Heatmap](../playbooks/finance_product_cost_margin.md)

> **Target Collection:** `Finance`
> **Collection ID:** 92
> **Database:** `Sapo`
> **Role:** Merchandising Manager, Finance
> **Archetype:** Diagnostic / Variance Alert
> **Description:** Audience: Merchandising/Finance. Scope: Cross-segment SKU level. Câu hỏi: SKU nào margin tốt + COGS variance bất thường?

Dashboard phân tích margin và chi phí theo từng SKU — xác định sản phẩm có margin tốt, phát hiện bất thường COGS so với trung bình 3 tháng.

## Segmentation Scope

> **Scope:** `scope_sales` + `filter_has_cogs` · Layer 1.5 (Finance) · Suffix `[All]`
> **Why:** Product cost margin must cover all segments (retail + B2B) to give a true SKU-level profitability view. `has_cogs = true` required for valid margin calculation.
> **Ref:** [segments.md#filter_has_cogs](../semantic/segments.md#filter_has_cogs)

All margin queries: `WHERE scope_sales AND has_cogs`.

## 📂 Collection: Finance

---

### 🖥️ Dashboard: Product Cost-to-Margin Heatmap [Cross]

**Description**: Phân tích SKU margin + COGS variance: scatter margin vs revenue, top 50 SKU table, phân phối margin, cảnh báo COGS drift > 10%, và breakdown theo kênh. Loại trừ promo lines để phản ánh kinh tế sản phẩm thực.

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

---

#### Filter: Channel

```json metabase-filter
{
  "slug": "channel",
  "type": "string/=",
  "field_id": 349
}
```

---

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

#### ❓ Question: Total SKUs Sold

Tổng số SKU phân biệt có doanh thu trong kỳ (loại trừ promo lines).

**Domain Reference**: [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku)

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
{ "row": 2, "col": 0, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Avg Margin %

Trung bình margin gộp toàn bộ SKU trong kỳ.

**Domain Reference**: [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku)

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
      "Avg Margin %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 2, "col": 4, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: Margin Outlier Count

Số SKU có gross margin < 10% — cần điều tra ngay.

**Domain Reference**: [Margin Outlier Flag](../domains/finance.md#m5-margin-outlier-flag-cờ-margin-bất-thường)

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
{ "row": 2, "col": 8, "size_x": 4, "size_y": 3 }
```

---

#### ❓ Question: COGS Variance Alert Count

Số SKU có COGS per unit tháng hiện tại lệch > 10% so với trung bình 3 tháng trước.

**Domain Reference**: [COGS Variance vs 3-Month Average](../domains/finance.md#m3-cogs-variance-vs-3-month-average-sai-lệch-giá-vốn-so-với-trung-bình-3-tháng)

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
{ "row": 2, "col": 12, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Scatter Section

SKU Margin vs Revenue — mỗi điểm là 1 SKU (30 ngày gần nhất)

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: SKU Margin vs Revenue Scatter

Scatter: X = doanh thu, Y = margin %, kích thước = số đơn, màu = kênh. Last 30 days.

**Domain Reference**: [SKU Revenue Share](../domains/finance.md#m4-sku-revenue-share-tỷ-trọng-doanh-thu-sku)

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
      "Gross Margin %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### 📝 Text: Top 50 SKU Table

Top 50 SKU — doanh thu, giá vốn, margin, COGS variance

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Top 50 SKU Detail Table

Table: SKU × Revenue × COGS × Margin % × COGS variance vs 3-month avg. Conditional formatting cho margin thấp và COGS spike.

**Domain Reference**: [COGS Variance vs 3-Month Average](../domains/finance.md#m3-cogs-variance-vs-3-month-average-sai-lệch-giá-vốn-so-với-trung-bình-3-tháng)

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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Margin Distribution

Phân phối margin — bao nhiêu SKU ở từng nhóm?

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 9, "size_y": 1 }
```

---

#### ❓ Question: Margin Distribution Histogram

Phân phối SKU theo nhóm margin — chia bucket 10%.

**Domain Reference**: [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku)

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
    "graph.y_axis.title_text": "So luong SKU",
    "table.column_formatting": [
      {
        "columns": ["Nhom margin"],
        "type": "single",
        "operator": "=",
        "value": "0–10% (alert)",
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 9, "size_y": 7 }
```

---

#### 📝 Text: COGS Variance Alert

COGS spike alert — SKU COGS tháng này vs trung bình 3 tháng > 10%

```json metabase-pos
{ "row": 25, "col": 9, "size_x": 9, "size_y": 1 }
```

---

#### ❓ Question: COGS Variance Alert Table

SKU có COGS/unit tháng này lệch > 10% so với avg 3 tháng trước — sorted by absolute variance desc.

**Domain Reference**: [COGS Variance vs 3-Month Average](../domains/finance.md#m3-cogs-variance-vs-3-month-average-sai-lệch-giá-vốn-so-với-trung-bình-3-tháng)

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
{ "row": 26, "col": 9, "size_x": 9, "size_y": 7 }
```

---

#### 📝 Text: SKU by Channel Breakdown

SKU breakdown theo kênh — margin so sánh cross-channel

```json metabase-pos
{ "row": 33, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: SKU Margin by Channel

Top 20 SKU có doanh thu cao nhất — margin % breakdown per channel. Giúp thấy SKU nào cùng một sản phẩm nhưng margin khác nhau theo kênh (pricing policy khác biệt).

**Domain Reference**: [SKU Gross Margin %](../domains/finance.md#m1-sku-gross-margin--biên-lợi-nhuận-gộp-theo-sku)

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
    },
    "table.column_formatting": [
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 10,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 34, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Source & Freshness

**Source:** int_misa_sales_lines · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line · **Caveats:** SKU-level margin
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


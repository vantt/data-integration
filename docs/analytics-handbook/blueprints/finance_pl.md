---
primary_scope: scope_sales
scope_indicator: "[All]"
layer: L1.5
uses_concepts: [scope_sales, filter_has_cogs, net_revenue, gross_profit, cogs_amount]
---

# Finance P&L [All] Blueprint

**Design Spec**: [Finance P&L Dashboard](../designs/finance_pl.md)

Dashboard P&L tai chinh toan cong ty — doanh thu thuan, gia von, loi nhuan gop, va chi phi nen tang Shopee. 3 tabs: tong quan P&L, loi nhuan theo kenh, kinh te Shopee. MoM comparison (last 30 days vs previous 30 days).

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` + `filter_has_cogs` · Layer L1.5 `[All]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales) · [`segments.md#filter_has_cogs`](../semantic/segments.md#filter_has_cogs)
> **Why:** Full P&L view across all sales channels. Revenue queries: `WHERE scope_sales`. Margin/profit queries additionally filter `has_cogs = true` (coverage ~65% of completed orders).
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`filter_has_cogs`](../semantic/segments.md#filter_has_cogs) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`gross_profit`](../semantic/metrics.md#gross_profit) · [`cogs_amount`](../semantic/metrics.md#cogs_amount)

Revenue SQL: `WHERE scope_sales`. P&L SQL: `WHERE scope_sales AND has_cogs`. Do not re-derive `is_sales_channel` or `status NOT IN (...)` inline.
## 📂 Collection: Executive

### 🖥️ Dashboard: Finance P&L [All]

**Description**: P&L tai chinh — doanh thu, gia von, loi nhuan gop, hieu qua kenh ban hang, va chi phi nen tang Shopee. Danh cho CFO/CEO trong buoi MBR hang thang.

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past30days",
  "field_id": 848,
  "field_id_map": {
    "int_misa_sales_lines": 324,
    "int_shopee_order_fees": 287,
    "fact_orders": 848
  }
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

### 📑 Tab: P&L Overview

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start, MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
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

#### 📝 Text: PL Overview Heading

## Doanh thu va loi nhuan gop — ket qua kinh doanh ky nay

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Net Revenue MTD

Hero metric — doanh thu thuan ky nay vs ky truoc + cung ky nam truoc. Exclude cancelled/voided orders.

```sql
-- YoY added 2026-05-28: filter-independent YoY uses fixed closed-month windows
WITH
filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start, MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) AS val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) AS val
    FROM fact_orders, filter_bounds
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND ordered_at >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND ordered_at <  filter_bounds.p_start
      [[AND {{channel}}]]
),
-- YoY: same closed month, prior year (last full month -12 months)
prev_year AS (
    SELECT COALESCE(SUM(net_revenue), 0) AS val
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND ordered_at <  date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    t.val                                                                    AS "Doanh thu thuan",
    p.val                                                                    AS "Ky truoc",
    py.val                                                                   AS "Cung ky nam truoc",
    ROUND((t.val - p.val)  * 100.0 / NULLIF(p.val,  0), 1)                  AS "MoM %",
    ROUND((t.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)                  AS "YoY %"
FROM this_period t, prev_period p, prev_year py
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Doanh thu thuan": {
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
{"row": 3, "col": 0, "size_x": 9, "size_y": 4}
```

#### ❓ Question: Gross Margin Percent

Gauge — bien lai gop % so voi nguong 40%. Green >40%, yellow 25-40%, red <25%.

```sql
SELECT
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Bien lai gop %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,  "max": 25,  "color": "#EF8C8C", "label": "Thap" },
      { "min": 25, "max": 40,  "color": "#F9D45C", "label": "Can canh bao" },
      { "min": 40, "max": 100, "color": "#84BB4C", "label": "Dat target" }
    ],
    "column_settings": {
      "Bien lai gop %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col": 9, "size_x": 9, "size_y": 4}
```

#### ❓ Question: COGS MTD

Supporting KPI — tong gia von hang ban ky nay vs ky truoc tu MISA. Exclude promo lines.

```sql
WITH
filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(cogs_amount), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(cogs_amount), 0) AS val
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND posting_date >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND posting_date <  filter_bounds.p_start
      [[AND {{channel}}]]
)
SELECT
    t.val AS "Gia von",
    p.val AS "Ky truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Gia von": {
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
{"row": 7, "col": 0, "size_x": 9, "size_y": 4}
```

#### ❓ Question: Gross Profit MTD

Supporting KPI — loi nhuan gop ky nay vs ky truoc + cung ky nam truoc. Exclude promo lines.

```sql
-- YoY added 2026-05-28
WITH
filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(gross_profit), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(gross_profit), 0) AS val
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND posting_date >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND posting_date <  filter_bounds.p_start
      [[AND {{channel}}]]
),
prev_year AS (
    SELECT COALESCE(SUM(gross_profit), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND posting_date <  date_trunc('month', current_date) - INTERVAL '12 months'
)
SELECT
    t.val                                                                    AS "Loi nhuan gop",
    p.val                                                                    AS "Ky truoc",
    py.val                                                                   AS "Cung ky nam truoc",
    ROUND((t.val - p.val)  * 100.0 / NULLIF(p.val,  0), 1)                  AS "MoM %",
    ROUND((t.val - py.val) * 100.0 / NULLIF(py.val, 0), 1)                  AS "YoY %"
FROM this_period t, prev_period p, prev_year py
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Loi nhuan gop": {
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
{"row": 7, "col": 9, "size_x": 9, "size_y": 4}
```

#### 📝 Text: PL Trend Heading

## Xu huong doanh thu va gia von — margin co duy tri?

```json metabase-pos
{"row": 11, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Revenue vs COGS Trend

Combo chart — doanh thu (bar) va gia von (line) theo thang. Two CTEs unioned then pivoted via monthly aggregation. Revenue from fact_orders, COGS from int_misa_sales_lines. Fixed 13-month window — trend chart shows full year context regardless of filter.

```sql
WITH revenue_monthly AS (
    SELECT
        date_trunc('month', ordered_at) AS "Thang",
        SUM(net_revenue)                     AS "Doanh thu thuan",
        NULL::DOUBLE                         AS "Gia von"
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND ordered_at >= date_trunc('month', current_date) - INTERVAL '12 months'
    GROUP BY 1
),
cogs_monthly AS (
    SELECT
        date_trunc('month', posting_date) AS "Thang",
        NULL::DOUBLE                      AS "Doanh thu thuan",
        SUM(cogs_amount)                  AS "Gia von"
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '12 months'
    GROUP BY 1
),
combined AS (
    SELECT * FROM revenue_monthly
    UNION ALL
    SELECT * FROM cogs_monthly
)
SELECT
    "Thang",
    SUM("Doanh thu thuan") AS "Doanh thu thuan",
    SUM("Gia von")         AS "Gia von"
FROM combined
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Doanh thu thuan", "Gia von"],
    "series_settings": {
      "Doanh thu thuan": {
        "display": "bar",
        "color": "#509EE3"
      },
      "Gia von": {
        "display": "line",
        "color": "#EF8C8C"
      }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Doanh thu thuan": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Gia von": {
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
{"row": 12, "col": 0, "size_x": 12, "size_y": 6}
```

#### ❓ Question: Revenue Waterfall

Waterfall — thanh phan doanh thu: Gross → Chiet khau → Thue → Doanh thu thuan.

```sql
SELECT
    "Khoan muc",
    "Gia tri"
FROM (
    VALUES
        ('Doanh thu gop',
            (SELECT COALESCE(SUM(gross_revenue), 0)
             FROM fact_orders
             WHERE status NOT IN ('CANCELLED', 'Voided')
               [[AND {{date_range}}]]
            )
        ),
        ('Chiet khau',
            (SELECT COALESCE(-SUM(ABS(discount_amount)), 0)
             FROM fact_orders
             WHERE status NOT IN ('CANCELLED', 'Voided')
               [[AND {{date_range}}]]
            )
        ),
        ('Thue VAT',
            (SELECT COALESCE(-SUM(ABS(vat_amount)), 0)
             FROM fact_orders
             WHERE status NOT IN ('CANCELLED', 'Voided')
               [[AND {{date_range}}]]
            )
        ),
        ('Doanh thu thuan',
            (SELECT COALESCE(SUM(net_revenue), 0)
             FROM fact_orders
             WHERE status NOT IN ('CANCELLED', 'Voided')
               [[AND {{date_range}}]]
            )
        )
) AS t("Khoan muc", "Gia tri")
```

```json metabase-viz
{
  "display": "waterfall",
  "visualization_settings": {
    "graph.dimensions": ["Khoan muc"],
    "graph.metrics": ["Gia tri"],
    "waterfall.increase_color": "#84BB4C",
    "waterfall.decrease_color": "#EF8C8C",
    "waterfall.total_color": "#509EE3",
    "column_settings": {
      "Gia tri": {
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
{"row": 12, "col": 12, "size_x": 6, "size_y": 6}
```

---

#### 📝 Text: Boi canh mua vu — Seasonal Context

**Bối cảnh mùa vụ VN Retail** — ưu tiên YoY khi xem tháng có seasonal event: Tết (Jan cuối/Feb đầu) — spike pre-Tết, gần-zero tuần Tết, Feb chậm; 9/9 · 10/10 · **11/11** · 12/12 Shopee Mega Sale — spike 3-10x; Black Friday cuối Nov. Nếu tháng có seasonal event → **ưu tiên YoY %, không trust MoM % standalone.** Caveat: MISA COGS coverage ~65% — YoY Gross Profit chỉ tin cậy nếu coverage năm trước tương đương.

```json metabase-pos
{"row": 97, "col": 0, "size_x": 18, "size_y": 2}
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + int_misa_sales_lines · **Cadence:** monthly · **Scope:** is_sales_channel=true · **Caveats:** MISA COGS coverage ~65%
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Channel Profitability

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
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

#### 📝 Text: Channel Heading

## Loi nhuan theo kenh ban hang — kenh nao hieu qua nhat?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Margin by Channel

Hero horizontal-bar — margin % theo kenh, sorted descending. Conditional coloring: green >40%, red <25%.

```sql
SELECT
    channel_name                                                          AS "Kenh ban hang",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    )                                                                     AS "Bien lai gop %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND channel_name IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh ban hang"],
    "graph.metrics": ["Bien lai gop %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Bien lai gop (%)",
    "column_settings": {
      "Bien lai gop %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Bien lai gop %"],
        "type": "single",
        "operator": ">=",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Bien lai gop %"],
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
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Revenue vs COGS by Channel

Grouped bar — doanh thu vs gia von theo kenh. Revenue from MISA revenue_net_of_discount, COGS from cogs_amount.

```sql
SELECT
    channel_name          AS "Kenh ban hang",
    SUM(revenue_net_of_discount) AS "Doanh thu",
    SUM(cogs_amount)      AS "Gia von"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND channel_name IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Kenh ban hang"],
    "graph.metrics": ["Doanh thu", "Gia von"],
    "series_settings": {
      "Doanh thu": { "color": "#509EE3" },
      "Gia von":   { "color": "#EF8C8C" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Gia von": {
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
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Channel Trend Heading

## Xu huong margin kenh — kenh nao dang cai thien?

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: COGS Ratio Trend

Multi-line — ty le gia von / doanh thu (%) theo thang, phan ra tung kenh ban hang.

```sql
SELECT
    date_trunc('month', posting_date) AS "Thang",
    channel_name                      AS "Kenh ban hang",
    ROUND(
        SUM(cogs_amount) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    )                                 AS "Ty le gia von %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND channel_name IS NOT NULL
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang", "Kenh ban hang"],
    "graph.metrics": ["Ty le gia von %"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "COGS Ratio (%)",
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5", "#F2A86F"],
    "column_settings": {
      "Ty le gia von %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Source & Freshness

**Source:** fact_orders + int_misa_sales_lines · **Cadence:** monthly · **Scope:** is_sales_channel=true · **Caveats:** MISA COGS coverage ~65%
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Shopee Economics


#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(payout_released_at)::DATE AS p_start, MAX(payout_released_at)::DATE AS p_end
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
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

#### 📝 Text: Shopee Heading

## Chi phi ban hang tren Shopee — phi san chiem bao nhieu?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Shopee Settlement MTD

Hero metric — tong tien thuc nhan tu Shopee ky nay vs ky truoc. Only released payouts.

```sql
WITH
filter_bounds AS (
    SELECT MIN(payout_released_at)::DATE AS p_start, MAX(payout_released_at)::DATE AS p_end
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(net_settlement), 0) AS val
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(net_settlement), 0) AS val
    FROM int_shopee_order_fees, filter_bounds
    WHERE payout_released_at IS NOT NULL
      AND payout_released_at >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND payout_released_at <  filter_bounds.p_start
      [[AND {{channel}}]]
)
SELECT
    t.val AS "Tien thuc nhan",
    p.val AS "Ky truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tien thuc nhan": {
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
{ "row": 3, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Settlement Margin Percent

Gauge — ty le net_settlement / gross_revenue. Green >75%, yellow 60-75%, red <60%.

```sql
SELECT
    ROUND(
        SUM(net_settlement) * 100.0 / NULLIF(SUM(gross_revenue), 0),
        1
    ) AS "Ty le thuc nhan %"
FROM int_shopee_order_fees
WHERE payout_released_at IS NOT NULL
  [[AND {{date_range}}]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,  "max": 60,  "color": "#EF8C8C", "label": "Thap" },
      { "min": 60, "max": 75,  "color": "#F9D45C", "label": "Can xem lai" },
      { "min": 75, "max": 100, "color": "#84BB4C", "label": "Tot" }
    ],
    "column_settings": {
      "Ty le thuc nhan %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Platform Fee Rate

Supporting KPI — tong phi san / doanh thu gop (%) ky nay vs ky truoc.

```sql
WITH
filter_bounds AS (
    SELECT MIN(payout_released_at)::DATE AS p_start, MAX(payout_released_at)::DATE AS p_end
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT
        ROUND(
            SUM(ABS(total_platform_fees) + ABS(infrastructure_fee) + ABS(voucher_xtra_fee)) * 100.0
            / NULLIF(SUM(gross_revenue), 0),
            1
        ) AS val
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
),
prev_period AS (
    SELECT
        ROUND(
            SUM(ABS(total_platform_fees) + ABS(infrastructure_fee) + ABS(voucher_xtra_fee)) * 100.0
            / NULLIF(SUM(gross_revenue), 0),
            1
        ) AS val
    FROM int_shopee_order_fees, filter_bounds
    WHERE payout_released_at IS NOT NULL
      AND payout_released_at >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND payout_released_at <  filter_bounds.p_start
      [[AND {{channel}}]]
)
SELECT
    t.val AS "Ty le phi san %",
    p.val AS "Ky truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Ty le phi san %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Shopee Gross Revenue

Supporting KPI — tong doanh thu gop Shopee ky nay vs ky truoc.

```sql
WITH
filter_bounds AS (
    SELECT MIN(payout_released_at)::DATE AS p_start, MAX(payout_released_at)::DATE AS p_end
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) AS val
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) AS val
    FROM int_shopee_order_fees, filter_bounds
    WHERE payout_released_at IS NOT NULL
      AND payout_released_at >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND payout_released_at <  filter_bounds.p_start
      [[AND {{channel}}]]
)
SELECT
    t.val AS "Doanh thu gop Shopee",
    p.val AS "Ky truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Doanh thu gop Shopee": {
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
{ "row": 7, "col": 0, "size_x": 9, "size_y": 4 }
```

#### 📝 Text: Shopee Fee Heading

## Cau truc phi — loai phi nao chiem nhieu nhat?

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Shopee Fee Breakdown

Horizontal-bar — ranking tung loai phi theo gia tri tuyet doi, sorted descending.

```sql
SELECT
    "Loai phi",
    "Gia tri phi"
FROM (
    SELECT
        'Service Fee'        AS "Loai phi",
        SUM(ABS(service_fee))         AS "Gia tri phi"
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Payment Fee',
        SUM(ABS(payment_fee))
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Fixed Fee',
        SUM(ABS(fixed_fee))
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Infrastructure Fee',
        SUM(ABS(infrastructure_fee))
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Voucher Xtra Fee',
        SUM(ABS(voucher_xtra_fee))
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'VAT Tax',
        SUM(ABS(vat_tax))
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Personal Income Tax',
        SUM(ABS(personal_income_tax))
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
) fees
WHERE "Gia tri phi" > 0
ORDER BY "Gia tri phi" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loai phi"],
    "graph.metrics": ["Gia tri phi"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5", "#F2A86F", "#F9D45C", "#EF8C8C", "#98D9D9"],
    "graph.x_axis.title_text": "Gia tri phi (VND)",
    "column_settings": {
      "Gia tri phi": {
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
{ "row": 12, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Revenue to Settlement Waterfall

Waterfall — dong tien tu Gross Revenue → tru cac loai phi → Net Settlement.

```sql
SELECT
    "Khoan muc",
    "Gia tri"
FROM (
    SELECT
        'Doanh thu gop'  AS "Khoan muc",
        SUM(gross_revenue) AS "Gia tri"
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Phi dich vu',
        SUM(total_platform_fees)
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Phi ha tang & Voucher',
        SUM(-(ABS(infrastructure_fee) + ABS(voucher_xtra_fee)))
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Phi van chuyen',
        SUM(total_shipping_net)
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Chiet khau & Khuyen mai',
        SUM(total_discounts)
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Thue',
        SUM(total_taxes)
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
    UNION ALL
    SELECT
        'Tien thuc nhan',
        SUM(net_settlement)
    FROM int_shopee_order_fees
    WHERE payout_released_at IS NOT NULL
      [[AND {{date_range}}]]
) AS wf
```

```json metabase-viz
{
  "display": "waterfall",
  "visualization_settings": {
    "graph.dimensions": ["Khoan muc"],
    "graph.metrics": ["Gia tri"],
    "waterfall.increase_color": "#84BB4C",
    "waterfall.decrease_color": "#EF8C8C",
    "waterfall.total_color": "#509EE3",
    "column_settings": {
      "Gia tri": {
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
{ "row": 12, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + int_misa_sales_lines · **Cadence:** monthly · **Scope:** is_sales_channel=true · **Caveats:** MISA COGS coverage ~65%
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

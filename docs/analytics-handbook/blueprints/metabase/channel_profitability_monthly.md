---
primary_scope: scope_sales
scope_indicator: "[Cross]"
layer: L3
uses_concepts: [scope_sales, filter_has_cogs, net_revenue, gross_profit, channel_net_profit, cogs_amount]
---

# Channel Profitability Monthly [Cross] Blueprint

**Design Spec**: [Channel Profitability Monthly](../designs/channel_profitability_monthly.md)

Dashboard bien loi nhuan gop theo kenh ban hang — gross margin, doanh thu, COGS, xu huong theo thang, phan tich san pham. Dung cho MBR review hang thang.

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_sales` + `filter_has_cogs` · Layer L3 `[Cross]` · [`segments.md#scope_sales`](../semantic/segments.md#scope_sales) · [`segments.md#filter_has_cogs`](../semantic/segments.md#filter_has_cogs)
> **Why:** Channel profitability compares performance across all sales channels (online, social, direct, wholesale). Requires all segments to properly attribute channel-level revenue and margin.
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`filter_has_cogs`](../semantic/segments.md#filter_has_cogs) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`gross_profit`](../semantic/metrics.md#gross_profit) · [`channel_net_profit`](../semantic/metrics.md#channel_net_profit) · [`cogs_amount`](../semantic/metrics.md#cogs_amount)

Revenue: `WHERE scope_sales`. Margin: `WHERE scope_sales AND has_cogs`. Channel breakdown via `channel_name` or `channel_category`.
## 📂 Collection: Analytics

### Dashboard: Channel Profitability Monthly [Cross]

**Description**: Bien loi nhuan gop theo kenh — tong quan, so sanh cross-channel, xu huong MoM, va phan tich san pham anh huong loi nhuan. Danh cho CEO, Finance, Sales Director.

> **⚠️ US CrossBorder excluded** — US CrossBorder orders have no MISA COGS postings (export/arrangement channel). Revenue from this channel now lives in `fact_us_shipment_economics` but gross margin is incalculable without COGS. **Do not add US to this report until MISA covers US orders.** See [US CrossBorder Operations](us_crossborder_operations.md) for US revenue tracking.

---

#### Filter: Period




```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past3months",
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

### 📑 Tab: Channel Overview

#### 📝 Text: > **US CrossBorder không có trong báo cáo này.** Kênh này không có dữ liệu MISA (đơn xuất khẩu/sắp xếp, không phải bán lẻ nội địa). Doanh thu US thực tế xem tại dashboard **US CrossBorder Operations**.



> **US CrossBorder không có trong báo cáo này.** Kênh này không có dữ liệu MISA (đơn xuất khẩu/sắp xếp, không phải bán lẻ nội địa). Doanh thu US thực tế xem tại dashboard **US CrossBorder Operations**.

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
-- Derive clean period boundaries from raw data dates:
-- weekly  (duration ≤ 6d)                    → Mon–Sun of data's week
-- closed  (p_end > 30d ago, non-weekly)       → 1st of month .. last day of p_end's month
-- this year   (recent, starts Jan, >100d)     → 01/01 .. 31/12
-- this quarter (recent, 35–100d)              → 01/Qstart .. last day of quarter
-- everything else (this month, past12m, …)   → 1st of month .. last day of p_end's month
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
-- n_months uses adjusted p_start/p_end so prev_start aligns to period boundary
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
{
  "display": "scalar",
  "visualization_settings": {
    "dashcard.background": false
  }
}
```

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### 📝 Text: **Bối cảnh mùa vụ VN Retail** — ưu tiên YoY khi xem tháng có seasonal event: Tết (Jan cuối/Feb đầu); 9/9 · 10/10 · **11/11** · 12/12 Shopee Mega Sale; Black Friday cuối Nov. Nếu tháng có seasonal event → **ưu tiên YoY %, không trust MoM % standalone.** ⚠ Caveat: Blueprint này là candidate for deprecation (audit 2026-05) — overlap với finance_channel_pl. YoY added as quick value trong khi pending consolidation. MISA COGS coverage ~65%.



**Bối cảnh mùa vụ VN Retail** — ưu tiên YoY khi xem tháng có seasonal event: Tết (Jan cuối/Feb đầu); 9/9 · 10/10 · **11/11** · 12/12 Shopee Mega Sale; Black Friday cuối Nov. Nếu tháng có seasonal event → **ưu tiên YoY %, không trust MoM % standalone.** ⚠ Caveat: Blueprint này là candidate for deprecation (audit 2026-05) — overlap với finance_channel_pl. YoY added as quick value trong khi pending consolidation. MISA COGS coverage ~65%.

```json metabase-pos
{
  "row": 4,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### 📝 Text: Bien loi nhuan gop theo kenh — kenh nao hieu qua nhat?



## Bien loi nhuan gop theo kenh — kenh nao hieu qua nhat?

```json metabase-pos
{
  "row": 6,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### Question: Gross Margin %




Hero gauge — bien loi nhuan gop tong hop, so sanh voi nguong 40%.

```sql
SELECT
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Gross Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      {
        "min": 0,
        "max": 25,
        "color": "#EF8C8C",
        "label": "Thap"
      },
      {
        "min": 25,
        "max": 40,
        "color": "#F9D45C",
        "label": "Trung binh"
      },
      {
        "min": 40,
        "max": 100,
        "color": "#84BB4C",
        "label": "Tot"
      }
    ]
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 0,
  "size_x": 6,
  "size_y": 4
}
```

#### Question: Total Revenue




Supporting KPI — tong doanh thu ky nay vs ky truoc + cung ky nam truoc.

```sql
-- YoY added 2026-05-28; note: blueprint deprecation candidate per audit — YoY added as quick value while pending
-- YoY window is filter-independent (last closed month -12 months) since {{date_range}} can't be shifted 12 months
WITH
filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND posting_date >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND posting_date <  filter_bounds.p_start
      [[AND {{channel}}]]
),
prev_year AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '13 months'
      AND posting_date <  date_trunc('month', current_date) - INTERVAL '12 months'
      [[AND {{channel}}]]
)
SELECT
    t.val                                                                    AS "Doanh thu",
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
      "[\"name\",\"Doanh thu\"]": {
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
{
  "row": 7,
  "col": 6,
  "size_x": 6,
  "size_y": 4
}
```

#### Question: Total COGS




Supporting KPI — tong gia von ky nay vs ky truoc.

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
      [[AND {{channel}}]]
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
    p.val AS "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Gia von\"]": {
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
{
  "row": 7,
  "col": 12,
  "size_x": 3,
  "size_y": 4
}
```

#### Question: Total Gross Profit




Supporting KPI — tong lai gop ky nay vs ky truoc.

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
    SELECT COALESCE(SUM(gross_profit), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(gross_profit), 0) AS val
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND posting_date >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND posting_date <  filter_bounds.p_start
      [[AND {{channel}}]]
)
SELECT
    t.val AS "Lai gop",
    p.val AS "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Lai gop\"]": {
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
{
  "row": 7,
  "col": 15,
  "size_x": 3,
  "size_y": 4
}
```

---

#### 📝 Text: So sanh hieu qua giua cac kenh ban hang



## So sanh hieu qua giua cac kenh ban hang

```json metabase-pos
{
  "row": 11,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### Question: Margin by Channel




Horizontal bar — ranking kenh theo gross margin %, highlight vuot nguong va canh bao.

```sql
SELECT
    channel_name AS "Kenh",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Gross Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY channel_name
ORDER BY "Gross Margin %" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": [
      "Kenh"
    ],
    "graph.colors": [
      "#509EE3"
    ],
    "graph.x_axis.title_text": "Gross Margin (%)",
    "graph.y_axis.title_text": "",
    "table.column_formatting": [
      {
        "columns": [
          "Gross Margin %"
        ],
        "type": "single",
        "operator": ">=",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": [
          "Gross Margin %"
        ],
        "type": "single",
        "operator": "<",
        "value": 25,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Gross Margin %\"]": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    },
    "graph.metrics": [
      "Gross Margin %"
    ]
  }
}
```

```json metabase-pos
{
  "row": 12,
  "col": 0,
  "size_x": 9,
  "size_y": 6
}
```

#### Question: Revenue vs COGS by Channel




Grouped bar — doanh thu va gia von tung kenh, so sanh scale.

```sql
SELECT
    channel_name                               AS "Kenh",
    SUM(revenue_net_of_discount)               AS "Doanh thu",
    SUM(cogs_amount)                           AS "Gia von"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY channel_name
ORDER BY "Doanh thu" DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": [
      "Kenh"
    ],
    "graph.colors": [
      "#509EE3",
      "#EF8C8C"
    ],
    "stackable.stack_type": null,
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "[\"name\",\"Doanh thu\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gia von\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "Doanh thu",
      "Gia von"
    ]
  }
}
```

```json metabase-pos
{
  "row": 12,
  "col": 9,
  "size_x": 9,
  "size_y": 6
}
```

---

#### 📝 Text: **Source:** fact_order_economics + dim_channels · **Cadence:** monthly · **Scope:** is_sales_channel + has_cogs · **Caveats:** MISA coverage gap



**Source:** fact_order_economics + dim_channels · **Cadence:** monthly · **Scope:** is_sales_channel + has_cogs · **Caveats:** MISA coverage gap

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Trends & Product Detail

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
)
SELECT '📅 Kỳ báo cáo: ' ||
    strftime(
      CASE WHEN (p_end - p_start)::INTEGER <= 6
        THEN date_trunc('week',  p_start)::DATE
        ELSE date_trunc('month', p_start)::DATE
      END, '%d/%m/%Y') || ' – ' ||
    strftime(
      CASE
        WHEN (p_end - p_start)::INTEGER <= 6
          THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
        WHEN p_end < current_date - 30
          THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
        WHEN (p_end - p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
          THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
        WHEN (p_end - p_start)::INTEGER BETWEEN 35 AND 100
          THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
        ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
      END, '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM filter_bounds
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "dashcard.background": false
  }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 2
}
```

---

#### 📝 Text: Xu huong margin theo kenh — kenh nao dang cai thien?



## Xu huong margin theo kenh — kenh nao dang cai thien?

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### Question: Margin Trend by Channel




Multi-line chart — bien dong gross margin % tung kenh theo thang.

```sql
SELECT
    date_trunc('month', posting_date)::date                        AS "Thang",
    channel_name                                                   AS "Kenh",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    )                                                              AS "Gross Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY date_trunc('month', posting_date), channel_name
ORDER BY "Thang" ASC, "Kenh" ASC
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": [
      "Thang",
      "Kenh"
    ],
    "graph.colors": [
      "#509EE3",
      "#88BDE6",
      "#A989C5",
      "#F2A86F"
    ],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Gross Margin (%)",
    "column_settings": {
      "[\"name\",\"Gross Margin %\"]": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    },
    "graph.metrics": [
      "Gross Margin %"
    ]
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 9,
  "size_y": 6
}
```

#### Question: Revenue Mix Trend




Stacked bar time — ty trong doanh thu tung kenh thay doi theo thang.

```sql
SELECT
    date_trunc('month', posting_date)::date AS "Thang",
    channel_name                            AS "Kenh",
    SUM(revenue_net_of_discount)            AS "Doanh thu"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY date_trunc('month', posting_date), channel_name
ORDER BY "Thang" ASC, "Kenh" ASC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": [
      "Thang",
      "Kenh"
    ],
    "graph.colors": [
      "#509EE3",
      "#88BDE6",
      "#A989C5",
      "#F2A86F"
    ],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Doanh thu (VND)",
    "column_settings": {
      "[\"name\",\"Doanh thu\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "Doanh thu"
    ]
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 9,
  "size_x": 9,
  "size_y": 6
}
```

---

#### 📝 Text: San pham anh huong loi nhuan — san pham nao tao lai, san pham nao keo xuong?



## San pham anh huong loi nhuan — san pham nao tao lai, san pham nao keo xuong?

```json metabase-pos
{
  "row": 9,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

#### Question: Top Products by Profit




Horizontal bar — top 15 san pham dong gop lai gop nhieu nhat.

```sql
SELECT
    product_name                AS "San pham",
    SUM(gross_profit)           AS "Lai gop"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name
ORDER BY "Lai gop" DESC
LIMIT 15
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": [
      "San pham"
    ],
    "graph.colors": [
      "#509EE3"
    ],
    "graph.x_axis.title_text": "Lai gop (VND)",
    "graph.y_axis.title_text": "",
    "column_settings": {
      "[\"name\",\"Lai gop\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "graph.metrics": [
      "Lai gop"
    ]
  }
}
```

```json metabase-pos
{
  "row": 10,
  "col": 0,
  "size_x": 9,
  "size_y": 9
}
```

#### Question: Low-Margin Products




Table with conditional formatting — san pham margin < 25%, can review gia/nguon cung. Do thi <15% do, >40% xanh.

```sql
SELECT
    product_name                                                        AS "San pham",
    channel_name                                                        AS "Kenh",
    SUM(revenue_net_of_discount)                                        AS "Doanh thu",
    SUM(gross_profit)                                                   AS "Lai gop",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    )                                                                   AS "Gross Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND {{date_range}}]]
  [[AND {{channel}}]]
GROUP BY product_name, channel_name
HAVING
    SUM(revenue_net_of_discount) > 0
    AND SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0) < 25
ORDER BY "Gross Margin %" ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "table.column_formatting": [
      {
        "columns": [
          "Gross Margin %"
        ],
        "type": "single",
        "operator": "<",
        "value": 15,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": [
          "Gross Margin %"
        ],
        "type": "single",
        "operator": ">=",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Doanh thu\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Lai gop\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Margin %\"]": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 10,
  "col": 9,
  "size_x": 9,
  "size_y": 9
}
```

---

#### 📝 Text: **Source:** fact_order_economics + dim_channels · **Cadence:** monthly · **Scope:** is_sales_channel + has_cogs · **Caveats:** MISA coverage gap



**Source:** fact_order_economics + dim_channels · **Cadence:** monthly · **Scope:** is_sales_channel + has_cogs · **Caveats:** MISA coverage gap

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

### 📑 Tab: Channel Profitability (Sapo)

#### 📝 Text: Kenh ban hang tin cay (Sapo) — Core vs Marketplace

**Nguồn: Sapo order data** (`fact_order_economics JOIN dim_channels`) — phân loại kênh đáng tin cậy (Core vs Marketplace dựa trên `is_marketplace`). Tab này thay thế tab MISA channel cũ (MISA ~95% UNKNOWN). Dữ liệu all-time (bộ lọc kỳ trên dashboard không áp dụng vào tab này vì cột date_key là INTEGER, không phải DATE — dùng Dashboard 77 nếu cần lọc theo kỳ cho Sapo channel data).

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 3
}
```

---

#### ❓ Question: Core vs Marketplace Summary

```sql
SELECT
    CASE WHEN dc.is_marketplace THEN 'Marketplace' ELSE 'Core' END  AS "Channel Type",
    SUM(foe.net_revenue)                                             AS "Net Revenue",
    SUM(foe.gross_profit)                                            AS "Gross Profit",
    ROUND(SUM(foe.gross_profit) * 100.0 / NULLIF(SUM(foe.net_revenue), 0), 1)              AS "Gross Margin %",
    ROUND(SUM(foe.channel_net_profit) * 100.0 / NULLIF(SUM(foe.net_revenue), 0), 1)        AS "Channel Net Margin %",
    ROUND(SUM(foe.fully_loaded_net_profit) * 100.0 / NULLIF(SUM(foe.net_revenue), 0), 1)   AS "Fully Loaded Margin %",
    COUNT(DISTINCT foe.order_id)                                     AS "Don hang"
FROM main_marts.fact_order_economics foe
JOIN main_marts.dim_channels dc USING (channel_key)
WHERE foe.has_cogs
  AND foe.scope_sales
  AND foe.is_active_order
GROUP BY 1
ORDER BY "Net Revenue" DESC
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
        "operator": ">=",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 25,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Net Revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Profit\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Channel Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Fully Loaded Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 3,
  "col": 0,
  "size_x": 18,
  "size_y": 4
}
```

---

#### ❓ Question: Per-Channel Profitability Table

```sql
SELECT
    dc.channel_name                                                                  AS "Kenh",
    CASE WHEN dc.is_marketplace THEN 'Marketplace' ELSE 'Core' END                  AS "Channel Type",
    SUM(foe.net_revenue)                                                             AS "Net Revenue",
    SUM(foe.gross_profit)                                                            AS "Gross Profit",
    ROUND(SUM(foe.gross_profit) * 100.0 / NULLIF(SUM(foe.net_revenue), 0), 1)       AS "Gross Margin %",
    ROUND(SUM(foe.channel_net_profit) * 100.0 / NULLIF(SUM(foe.net_revenue), 0), 1) AS "Channel Net Margin %",
    COUNT(DISTINCT foe.order_id)                                                     AS "Don hang"
FROM main_marts.fact_order_economics foe
JOIN main_marts.dim_channels dc USING (channel_key)
WHERE foe.has_cogs
  AND foe.scope_sales
  AND foe.is_active_order
GROUP BY dc.channel_name, dc.is_marketplace
ORDER BY "Net Revenue" DESC
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
        "operator": ">=",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 25,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Net Revenue\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Profit\"]": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "[\"name\",\"Gross Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "[\"name\",\"Channel Net Margin %\"]": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{
  "row": 7,
  "col": 0,
  "size_x": 18,
  "size_y": 8
}
```

---

#### ❓ Question: Monthly Revenue Trend — Core vs Marketplace

```sql
SELECT
    CAST((foe.date_key // 100) AS VARCHAR)                                          AS "Thang",
    CASE WHEN dc.is_marketplace THEN 'Marketplace' ELSE 'Core' END                  AS "Channel Type",
    SUM(foe.net_revenue)                                                             AS "Net Revenue"
FROM main_marts.fact_order_economics foe
JOIN main_marts.dim_channels dc USING (channel_key)
WHERE foe.has_cogs
  AND foe.scope_sales
  AND foe.is_active_order
GROUP BY foe.date_key // 100, dc.is_marketplace
ORDER BY "Thang" ASC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Thang", "Channel Type"],
    "graph.metrics": ["Net Revenue"],
    "graph.colors": ["#509EE3", "#F2A86F"],
    "graph.x_axis.title_text": "Thang (YYYYMM)",
    "graph.y_axis.title_text": "Net Revenue (VND)",
    "column_settings": {
      "[\"name\",\"Net Revenue\"]": {
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
{
  "row": 15,
  "col": 0,
  "size_x": 18,
  "size_y": 6
}
```

---

#### 📝 Text: **Source:** fact_order_economics + dim_channels (Sapo) · **Scope:** has_cogs AND scope_sales AND is_active_order · **Channel split:** is_marketplace (reliable) · **Date filter:** not wired (date_key is INTEGER); use Dashboard 77 for period-filtered Sapo channel analysis.

**Source:** `fact_order_economics JOIN dim_channels` (Sapo) · **Scope:** `has_cogs AND scope_sales AND is_active_order` · **Channel split:** `is_marketplace` — reliable Sapo-based classification. MISA channel (other tabs) ~95% UNKNOWN — không dùng để so sánh channel.

```json metabase-pos
{
  "row": 99,
  "col": 0,
  "size_x": 18,
  "size_y": 1
}
```

---

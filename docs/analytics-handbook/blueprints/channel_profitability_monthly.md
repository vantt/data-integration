# Channel Profitability Monthly Blueprint

**Design Spec**: [Channel Profitability Monthly](../designs/channel_profitability_monthly.md)

Dashboard bien loi nhuan gop theo kenh ban hang — gross margin, doanh thu, COGS, xu huong theo thang, phan tich san pham. Dung cho MBR review hang thang.

## 📂 Collection: Executive

### Dashboard: Channel Profitability Monthly

**Description**: Bien loi nhuan gop theo kenh — tong quan, so sanh cross-channel, xu huong MoM, va phan tich san pham anh huong loi nhuan. Danh cho CEO, Finance, Sales Director.

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past3months"
}
```

#### Filter: Channel

```json metabase-filter
{
  "slug": "channel",
  "type": "string/="
}
```

---

### 📑 Tab: Channel Overview

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
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Tab Overview Heading

Bien loi nhuan gop theo kenh — kenh nao hieu qua nhat?

```json metabase-pos
{"row":1, "col":0, "size_x":18, "size_y":1}
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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,  "max": 25, "color": "#EF8C8C", "label": "Thap" },
      { "min": 25, "max": 40, "color": "#F9D45C", "label": "Trung binh" },
      { "min": 40, "max": 100, "color": "#84BB4C", "label": "Tot" }
    ]
  }
}
```

```json metabase-pos
{"row":2, "col":0, "size_x":6, "size_y":5}
```

#### Question: Total Revenue

Supporting KPI — tong doanh thu ky nay vs ky truoc.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND posting_date >= {{date_range}}]]
      [[AND channel_name = {{channel}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '3 months'
      AND posting_date <  date_trunc('month', current_date)
      [[AND channel_name = {{channel}}]]
)
SELECT
    t.val AS "Doanh thu",
    p.val AS "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "Doanh thu": {
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
{"row":2, "col":6, "size_x":4, "size_y":3}
```

#### Question: Total COGS

Supporting KPI — tong gia von ky nay vs ky truoc.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(cogs_amount), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND posting_date >= {{date_range}}]]
      [[AND channel_name = {{channel}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(cogs_amount), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '3 months'
      AND posting_date <  date_trunc('month', current_date)
      [[AND channel_name = {{channel}}]]
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
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
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
{"row":2, "col":10, "size_x":4, "size_y":3}
```

#### Question: Total Gross Profit

Supporting KPI — tong lai gop ky nay vs ky truoc.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(gross_profit), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND posting_date >= {{date_range}}]]
      [[AND channel_name = {{channel}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(gross_profit), 0) AS val
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      AND posting_date >= date_trunc('month', current_date) - INTERVAL '3 months'
      AND posting_date <  date_trunc('month', current_date)
      [[AND channel_name = {{channel}}]]
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
    "scalar.comparisons": [
      {
        "id": "prev_period",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
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
{"row":2, "col":14, "size_x":4, "size_y":3}
```

#### 📝 Text: Channel Comparison Heading

So sanh hieu qua giua cac kenh ban hang

```json metabase-pos
{"row":7, "col":0, "size_x":18, "size_y":1}
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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
GROUP BY channel_name
ORDER BY "Gross Margin %" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Gross Margin %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Gross Margin (%)",
    "graph.y_axis.title_text": "",
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
      "Gross Margin %": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    }
  }
}
```

```json metabase-pos
{"row":8, "col":0, "size_x":9, "size_y":6}
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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
GROUP BY channel_name
ORDER BY "Doanh thu" DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Doanh thu", "Gia von"],
    "graph.colors": ["#509EE3", "#EF8C8C"],
    "stackable.stack_type": null,
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
{"row":8, "col":9, "size_x":9, "size_y":6}
```

---

### 📑 Tab: Trends & Product Detail
#### 📝 Text: Trends Heading

Xu huong margin theo kenh — kenh nao dang cai thien?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
GROUP BY date_trunc('month', posting_date), channel_name
ORDER BY "Thang" ASC, "Kenh" ASC
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang", "Kenh"],
    "graph.metrics": ["Gross Margin %"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5", "#F2A86F"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Gross Margin (%)",
    "column_settings": {
      "Gross Margin %": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 9, "size_y": 6 }
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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
GROUP BY date_trunc('month', posting_date), channel_name
ORDER BY "Thang" ASC, "Kenh" ASC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Thang", "Kenh"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5", "#F2A86F"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Doanh thu (VND)",
    "column_settings": {
      "Doanh thu": {
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
{ "row": 1, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Product Detail Heading

San pham anh huong loi nhuan — san pham nao tao lai, san pham nao keo xuong?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top Products by Profit

Horizontal bar — top 15 san pham dong gop lai gop nhieu nhat.

```sql
SELECT
    product_name                AS "San pham",
    SUM(gross_profit)           AS "Lai gop"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
GROUP BY product_name
ORDER BY "Lai gop" DESC
LIMIT 15
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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
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
        "columns": ["Gross Margin %"],
        "type": "single",
        "operator": "<",
        "value": 15,
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
      }
    ],
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Lai gop": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Gross Margin %": {
        "number_style": "percent",
        "decimals": 1,
        "scale": 0.01
      }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 9, "size_x": 9, "size_y": 9 }
```

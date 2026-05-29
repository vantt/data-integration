# Product Profitability Blueprint [All]

**Design Spec**: [Product Profitability](../designs/product_profitability.md)

Ranking san pham theo lai gop va margin — top/bottom products, chi tiet theo kenh. Dung int_misa_sales_lines (COGS per product line).

## 📂 Collection: Executive

### Dashboard: Product Profitability [All]

**Description**: San pham nao tao margin cao, san pham nao keo xuong — ranking, chi tiet, cross-channel. Danh cho Merchandising, Sales Director.

---

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 30 ngày gần nhất: ' ||
  strftime(current_date - 29, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  So sánh: ' ||
  strftime(current_date - 59, '%d/%m/%Y') || ' – ' || strftime(current_date - 30, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

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

#### 📝 Text: Dashboard Heading

San pham nao tao lai, san pham nao keo xuong?

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### Question: Total Products

So san pham co data COGS.

```sql
SELECT COUNT(DISTINCT product_name) AS "So san pham"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":4, "size_y":3}
```

#### Question: Avg Margin %

Hero — margin trung binh toan bo san pham.

```sql
SELECT
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Avg Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg Margin %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":4, "size_x":5, "size_y":3}
```

#### Question: Highest Margin Product

San pham margin cao nhat (min 3 lines de co y nghia).

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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
GROUP BY product_name
HAVING COUNT(*) >= 3
ORDER BY "Margin %" DESC
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "San pham",
    "scalar.comparisons": [
      {
        "id": "margin",
        "type": "anotherColumn",
        "column": "Margin %",
        "label": "margin"
      }
    ]
  }
}
```

```json metabase-pos
{"row": 3, "col":9, "size_x":5, "size_y":3}
```

#### Question: Lowest Margin Product

San pham margin thap nhat (min 3 lines).

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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
GROUP BY product_name
HAVING COUNT(*) >= 3
ORDER BY "Margin %" ASC
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "San pham",
    "scalar.comparisons": [
      {
        "id": "margin",
        "type": "anotherColumn",
        "column": "Margin %",
        "label": "margin"
      }
    ]
  }
}
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":3}
```

#### 📝 Text: Ranking Heading

Top 20 san pham theo lai gop

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":1}
```

#### Question: Top Products by Profit

Horizontal bar — top 20 san pham dong gop lai gop nhieu nhat.

```sql
SELECT
    product_name AS "San pham",
    SUM(gross_profit) AS "Lai gop"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  AND revenue_net_of_discount > 0
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
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
{"row": 7, "col":0, "size_x":9, "size_y":9}
```

#### Question: Bottom Margin Products

Horizontal bar — 20 san pham margin thap nhat.

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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
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
{"row": 7, "col":9, "size_x":9, "size_y":9}
```

#### 📝 Text: Detail Heading

Chi tiet san pham — margin, doanh thu, gia von theo kenh

```json metabase-pos
{"row": 16, "col":0, "size_x":18, "size_y":1}
```

#### Question: Product Detail Table

Table — full product breakdown with conditional formatting.

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
  [[AND posting_date >= {{date_range}}]]
  [[AND channel_name = {{channel}}]]
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
{"row": 17, "col":0, "size_x":18, "size_y":10}
```

#### 📝 Text: Source & Freshness

**Source:** int_misa_sales_lines · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line · **Caveats:** SKU-level COGS only
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


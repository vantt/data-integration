# Order Profitability Blueprint [All]

**Dashboard ID**: 45
**Scope**: scope_sales (`is_sales_channel = true`)
**Layer**: L1 - Executive
**Design Spec**: [Order Profitability](../designs/order_profitability.md)
**Related**: [Channel Explorer](order_profitability_channel_explorer.md) — no hardcoded scope, all channels

> Dashboard này analyze profitability across all customer types (RETAIL + B2B) on sales channels.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

P&L per order — gross margin, channel net profit, cost structure, order detail. Dung `fact_order_economics` (Sapo revenue + MISA COGS + Shopee fees).

## 📂 Collection: Executive

### Dashboard: Order Profitability [All]

**Description**: Loi nhuan don hang — tong quan P&L, so sanh kenh, chi tiet tung don. Danh cho CEO, CFO, Sales Director. **Scope: All sales channels, all customer types.**

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
{"row":0, "col":0, "size_x":18, "size_y":1}
```

---

#### 📝 Text: Section Heading — P&L Overview

## Tổng quan P&L
Lợi nhuận đơn hàng — gross margin, lãi ròng kênh, phủ COGS

```json metabase-pos
{"row":1, "col":0, "size_x":18, "size_y":1}
```

#### Question: Avg Gross Margin %

Hero gauge — bien lai gop trung binh cua don co COGS, so voi nguong 50%.

```sql
SELECT
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(net_revenue), 0),
        1
    ) AS "Gross Margin %"
FROM fact_order_economics
WHERE status = 'COMPLETED'
  AND has_cogs
  AND channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,  "max": 35, "color": "#EF8C8C", "label": "Thap" },
      { "min": 35, "max": 50, "color": "#F9D45C", "label": "Trung binh" },
      { "min": 50, "max": 100, "color": "#84BB4C", "label": "Tot" }
    ]
  }
}
```

```json metabase-pos
{"row":2, "col":0, "size_x":6, "size_y":4}
```

#### Question: Total Gross Profit

Supporting KPI — tong lai gop ky nay.

```sql
SELECT
    SUM(gross_profit) AS "Lai gop"
FROM fact_order_economics
WHERE status = 'COMPLETED'
  AND has_cogs
  AND channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Lai gop": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row":2, "col":6, "size_x":6, "size_y":2}
```

#### Question: Total Channel Net Profit

Supporting KPI — lai rong sau phi san.

```sql
SELECT
    SUM(channel_net_profit) AS "Lai rong kenh"
FROM fact_order_economics
WHERE status = 'COMPLETED'
  AND has_cogs
  AND channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Lai rong kenh": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row":2, "col":12, "size_x":6, "size_y":2}
```

#### Question: Orders with COGS

Coverage KPI — so don co MISA data (wide bottom KPI).

```sql
SELECT
    SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END) AS "Co COGS",
    COUNT(*) AS "Tong don",
    ROUND(SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS "Coverage %"
FROM fact_order_economics
WHERE status = 'COMPLETED'
  AND channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Co COGS",
    "scalar.comparisons": [
      { "id": "total", "type": "anotherColumn", "column": "Tong don", "label": "tong don" }
    ]
  }
}
```

```json metabase-pos
{"row":4, "col":6, "size_x":12, "size_y":2}
```

---

#### 📝 Text: Section Heading — Channel

## Lợi nhuận theo kênh
Kênh nào tạo giá trị thực sự?

```json metabase-pos
{"row":6, "col":0, "size_x":18, "size_y":1}
```

#### Question: Channel Net Margin %

Horizontal bar — ranking kenh theo channel net margin.

```sql
SELECT
    c.channel_name AS "Kenh",
    ROUND(
        SUM(e.channel_net_profit) * 100.0 / NULLIF(SUM(e.net_revenue), 0),
        1
    ) AS "Channel Net Margin %"
FROM fact_order_economics e
JOIN dim_channels c USING (channel_key)
WHERE e.status = 'COMPLETED'
  AND e.has_cogs
  AND c.is_sales_channel
  [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND c.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
GROUP BY c.channel_name
ORDER BY "Channel Net Margin %" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Channel Net Margin %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Channel Net Margin (%)",
    "graph.y_axis.title_text": "",
    "table.column_formatting": [
      { "columns": ["Channel Net Margin %"], "type": "single", "operator": ">=", "value": 50, "color": "#84BB4C", "highlight_row": false },
      { "columns": ["Channel Net Margin %"], "type": "single", "operator": "<",  "value": 25, "color": "#EF8C8C", "highlight_row": false }
    ]
  }
}
```

```json metabase-pos
{"row":7, "col":0, "size_x":9, "size_y":6}
```

#### Question: Cost Structure by Channel

Stacked bar — doanh thu, COGS, phi san theo kenh.

```sql
SELECT
    c.channel_name AS "Kenh",
    SUM(e.gross_profit) AS "Lai gop",
    SUM(e.cogs_amount) AS "Gia von",
    ABS(COALESCE(SUM(e.shopee_platform_fees), 0))
        + ABS(COALESCE(SUM(e.shopee_infra_fee), 0))
        + ABS(COALESCE(SUM(e.shopee_voucher_xtra_fee), 0))
        + ABS(COALESCE(SUM(e.shopee_taxes), 0))
        AS "Phi san"
FROM fact_order_economics e
JOIN dim_channels c USING (channel_key)
WHERE e.status = 'COMPLETED'
  AND e.has_cogs
  AND c.is_sales_channel
  [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND c.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
GROUP BY c.channel_name
ORDER BY SUM(e.net_revenue) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Lai gop", "Gia von", "Phi san"],
    "graph.colors": ["#84BB4C", "#EF8C8C", "#F9D45C"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Lai gop": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Gia von": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Phi san": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row":7, "col":9, "size_x":9, "size_y":6}
```

---

#### 📝 Text: Section Heading — Detail

## Chi tiết P&L từng đơn
Đơn nào lãi nhiều, đơn nào lỗ?

```json metabase-pos
{"row":13, "col":0, "size_x":18, "size_y":1}
```

#### Question: Margin Distribution

Histogram — phan bo gross margin % cua cac don hang.

```sql
SELECT
    CASE
        WHEN gross_margin_pct < 0    THEN '< 0% (Lo)'
        WHEN gross_margin_pct < 0.25 THEN '0-25%'
        WHEN gross_margin_pct < 0.50 THEN '25-50%'
        WHEN gross_margin_pct < 0.75 THEN '50-75%'
        ELSE '75-100%'
    END AS "Vung margin",
    COUNT(*) AS "So don"
FROM fact_order_economics
WHERE status = 'COMPLETED'
  AND has_cogs
  AND channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  [[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
GROUP BY 1
ORDER BY
    CASE "Vung margin"
        WHEN '< 0% (Lo)' THEN 1
        WHEN '0-25%' THEN 2
        WHEN '25-50%' THEN 3
        WHEN '50-75%' THEN 4
        ELSE 5
    END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Vung margin"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Gross Margin Range",
    "graph.y_axis.title_text": "So don hang"
  }
}
```

```json metabase-pos
{"row":14, "col":0, "size_x":9, "size_y":6}
```

#### Question: Profit by Date

Line chart — xu huong gross profit theo ngay.

```sql
SELECT
    d.date_actual AS "Ngay",
    SUM(e.gross_profit) AS "Lai gop"
FROM fact_order_economics e
JOIN dim_channels c USING (channel_key)
JOIN dim_date d ON e.date_key = d.date_key
WHERE e.status = 'COMPLETED'
  AND e.has_cogs
  AND c.is_sales_channel
  [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND e.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
GROUP BY d.date_actual
ORDER BY d.date_actual
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Lai gop"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Lai gop (VND)",
    "column_settings": {
      "Lai gop": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row":14, "col":9, "size_x":9, "size_y":6}
```

---

#### 📝 Text: Section Heading — Order List

## Danh sách đơn hàng
Sắp xếp theo lãi/lỗ — phát hiện đơn bất thường

```json metabase-pos
{"row":20, "col":0, "size_x":18, "size_y":1}
```

#### Question: Order P&L Table

Table with conditional formatting — chi tiet tung don hang.

```sql
SELECT
    e.order_code AS "Ma don",
    c.channel_name AS "Kenh",
    d.date_actual AS "Ngay",
    e.net_revenue AS "Doanh thu",
    e.cogs_amount AS "Gia von",
    e.gross_profit AS "Lai gop",
    ROUND(e.gross_margin_pct * 100, 1) AS "Gross Margin %",
    e.shopee_platform_fees AS "Phi san",
    e.channel_net_profit AS "Lai rong kenh",
    ROUND(e.channel_net_margin_pct * 100, 1) AS "Net Margin %"
FROM fact_order_economics e
JOIN dim_channels c USING (channel_key)
JOIN dim_date d ON e.date_key = d.date_key
WHERE e.status = 'COMPLETED'
  AND e.has_cogs
  AND c.is_sales_channel
  [[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
  [[AND c.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
ORDER BY e.gross_profit DESC
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
        "value": 20,
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
      "Doanh thu":    { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Gia von":      { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Lai gop":      { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Phi san":      { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Lai rong kenh":{ "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row":21, "col":0, "size_x":18, "size_y":10}
```

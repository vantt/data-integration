# Marketing ROI Blueprint

**Design Spec**: [Marketing ROI](../designs/marketing_roi.md)

ROAS per channel — tong spend vs revenue, xu huong, chi tiet per kenh. Dung fact_marketing_spend + fact_orders.

## 📂 Collection: Marketing & Customers

### Dashboard: Marketing ROI

**Description**: Hieu qua chi tieu marketing — ROAS, spend vs revenue, CPC/CPM theo kenh. Danh cho CMO, Marketing Manager.

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
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past30days"
}
```

---

#### 📝 Text: Dashboard Heading

Marketing ROI — chi tieu vs doanh thu theo kenh

```json metabase-pos
{"row":1, "col":0, "size_x":18, "size_y":1}
```

#### Question: Total Spend

Tong chi phi marketing.

```sql
SELECT SUM(spend_amount) AS "Tong chi phi"
FROM fact_marketing_spend
[[WHERE date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tong chi phi": {
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
{"row":2, "col":0, "size_x":6, "size_y":3}
```

#### Question: Total Revenue

Tong doanh thu cac kenh co spend.

```sql
SELECT SUM(o.net_revenue) AS "Tong doanh thu"
FROM fact_orders o
JOIN dim_channels c USING (channel_key)
WHERE o.status = 'COMPLETED'
  AND c.is_sales_channel
  [[AND o.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tong doanh thu": {
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
{"row":2, "col":6, "size_x":6, "size_y":3}
```

#### Question: Blended ROAS

Hero — ROAS tong hop = revenue / spend.

```sql
WITH spend AS (
    SELECT SUM(spend_amount) AS total_spend
    FROM fact_marketing_spend
    [[WHERE date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
),
revenue AS (
    SELECT SUM(o.net_revenue) AS total_revenue
    FROM fact_orders o
    JOIN dim_channels c USING (channel_key)
    WHERE o.status = 'COMPLETED'
      AND c.is_sales_channel
      [[AND o.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
)
SELECT
    ROUND(r.total_revenue::DOUBLE / NULLIF(s.total_spend, 0), 1) AS "ROAS"
FROM spend s, revenue r
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "ROAS": {
        "suffix": "x"
      }
    }
  }
}
```

```json metabase-pos
{"row":2, "col":12, "size_x":6, "size_y":3}
```

#### 📝 Text: Trend Heading

Chi tieu va doanh thu theo thoi gian

```json metabase-pos
{"row":5, "col":0, "size_x":18, "size_y":1}
```

#### Question: Spend vs Revenue Trend

Combo chart — revenue (bar) + spend (line) theo thang.

```sql
WITH monthly_spend AS (
    SELECT
        d.date_actual AS "Thang",
        SUM(m.spend_amount) AS "Chi phi"
    FROM fact_marketing_spend m
    JOIN dim_date d ON m.date_key = d.date_key
    [[WHERE m.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
    GROUP BY d.date_actual
),
monthly_revenue AS (
    SELECT
        d.date_actual AS "Thang",
        SUM(o.net_revenue) AS "Doanh thu"
    FROM fact_orders o
    JOIN dim_channels c USING (channel_key)
    JOIN dim_date d ON o.date_key = d.date_key
    WHERE o.status = 'COMPLETED'
      AND c.is_sales_channel
      [[AND o.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
    GROUP BY d.date_actual
)
SELECT
    COALESCE(s."Thang", r."Thang") AS "Thang",
    COALESCE(r."Doanh thu", 0) AS "Doanh thu",
    COALESCE(s."Chi phi", 0) AS "Chi phi"
FROM monthly_spend s
FULL OUTER JOIN monthly_revenue r USING ("Thang")
ORDER BY "Thang"
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Doanh thu", "Chi phi"],
    "series_settings": {
      "Doanh thu": { "display": "bar", "color": "#509EE3" },
      "Chi phi": { "display": "line", "color": "#EF8C8C" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Chi phi": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{"row":6, "col":0, "size_x":18, "size_y":6}
```

#### 📝 Text: Channel Heading

Hieu qua theo kenh quang cao

```json metabase-pos
{"row":12, "col":0, "size_x":18, "size_y":1}
```

#### Question: ROAS by Channel

Horizontal bar — ranking kenh theo ROAS.

```sql
WITH channel_spend AS (
    SELECT
        c.channel_name AS "Kenh",
        SUM(m.spend_amount) AS spend
    FROM fact_marketing_spend m
    JOIN dim_channels c USING (channel_key)
    [[WHERE m.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
    GROUP BY c.channel_name
),
channel_revenue AS (
    SELECT
        c.channel_name AS "Kenh",
        SUM(o.net_revenue) AS revenue
    FROM fact_orders o
    JOIN dim_channels c USING (channel_key)
    WHERE o.status = 'COMPLETED'
      AND c.is_sales_channel
      [[AND o.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
    GROUP BY c.channel_name
)
SELECT
    COALESCE(s."Kenh", r."Kenh") AS "Kenh",
    ROUND(COALESCE(r.revenue, 0)::DOUBLE / NULLIF(s.spend, 0), 1) AS "ROAS"
FROM channel_spend s
LEFT JOIN channel_revenue r USING ("Kenh")
WHERE s.spend > 0
ORDER BY "ROAS" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["ROAS"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "ROAS (x)",
    "graph.y_axis.title_text": "",
    "table.column_formatting": [
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
    ]
  }
}
```

```json metabase-pos
{"row":13, "col":0, "size_x":18, "size_y":6}
```

#### Question: Channel Marketing Table

Table — spend, revenue, ROAS, CPC, CPM per kenh.

```sql
WITH channel_spend AS (
    SELECT
        c.channel_name,
        SUM(m.spend_amount) AS spend,
        SUM(m.clicks) AS clicks,
        SUM(m.impressions) AS impressions
    FROM fact_marketing_spend m
    JOIN dim_channels c USING (channel_key)
    [[WHERE m.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
    GROUP BY c.channel_name
),
channel_revenue AS (
    SELECT
        c.channel_name,
        SUM(o.net_revenue) AS revenue,
        COUNT(DISTINCT o.order_id) AS orders
    FROM fact_orders o
    JOIN dim_channels c USING (channel_key)
    WHERE o.status = 'COMPLETED'
      AND c.is_sales_channel
      [[AND o.date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]
    GROUP BY c.channel_name
)
SELECT
    s.channel_name AS "Kenh",
    s.spend AS "Chi phi",
    COALESCE(r.revenue, 0) AS "Doanh thu",
    COALESCE(r.orders, 0) AS "Don hang",
    ROUND(COALESCE(r.revenue, 0)::DOUBLE / NULLIF(s.spend, 0), 1) AS "ROAS",
    CASE WHEN s.clicks > 0 THEN ROUND(s.spend::DOUBLE / s.clicks, 0) ELSE NULL END AS "CPC",
    CASE WHEN s.impressions > 0 THEN ROUND(s.spend::DOUBLE / s.impressions * 1000, 0) ELSE NULL END AS "CPM",
    s.clicks AS "Clicks",
    s.impressions AS "Impressions"
FROM channel_spend s
LEFT JOIN channel_revenue r USING (channel_name)
WHERE s.spend > 0
ORDER BY "ROAS" DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "table.column_formatting": [
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
        "highlight_row": true
      }
    ],
    "column_settings": {
      "Chi phi": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "CPC": { "number_style": "currency", "currency": "VND", "decimals": 0 },
      "CPM": { "number_style": "currency", "currency": "VND", "decimals": 0 }
    }
  }
}
```

```json metabase-pos
{"row":19, "col":0, "size_x":18, "size_y":8}
```

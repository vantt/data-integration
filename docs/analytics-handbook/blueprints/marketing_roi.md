# Marketing ROI Blueprint

**Design Spec**: [Marketing ROI](../designs/marketing_roi.md)

ROAS per channel — tong spend vs revenue, xu huong, chi tiet per kenh. Dung fact_marketing_spend + fact_orders.

## 📂 Collection: Marketing & Customers

### Dashboard: Marketing ROI [Retail]

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
  "default": "past30days"
}
```

---

#### 📝 Text: Dashboard Heading

Marketing ROI — chi tieu vs doanh thu theo kenh

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### Question: Total Spend

Tong chi phi marketing.

```sql
SELECT SUM(spend_amount) AS "Tong chi phi"
FROM fact_marketing_spend
[[WHERE date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
{"row": 3, "col":0, "size_x":6, "size_y":3}
```

#### Question: Total Revenue

Tong doanh thu cac kenh co spend.

```sql
SELECT SUM(o.net_revenue) AS "Tong doanh thu"
FROM fact_orders o
JOIN dim_channels c USING (channel_key)
WHERE o.status = 'COMPLETED'
  AND c.is_sales_channel
  [[AND o.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
{"row": 3, "col":6, "size_x":6, "size_y":3}
```

#### Question: Blended ROAS

Hero — ROAS tong hop = revenue / spend.

```sql
WITH spend AS (
    SELECT SUM(spend_amount) AS total_spend
    FROM fact_marketing_spend
    [[WHERE date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
),
revenue AS (
    SELECT SUM(o.net_revenue) AS total_revenue
    FROM fact_orders o
    JOIN dim_channels c USING (channel_key)
    WHERE o.status = 'COMPLETED'
      AND c.is_sales_channel
      [[AND o.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
{"row": 3, "col":12, "size_x":6, "size_y":3}
```

#### 📝 Text: Trend Heading

Chi tieu va doanh thu theo thoi gian

```json metabase-pos
{"row": 6, "col":0, "size_x":18, "size_y":1}
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
    [[WHERE m.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
      [[AND o.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
{"row": 7, "col":0, "size_x":18, "size_y":6}
```

#### 📝 Text: Channel Heading

Hieu qua theo kenh quang cao

```json metabase-pos
{"row": 13, "col":0, "size_x":18, "size_y":1}
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
    [[WHERE m.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
      [[AND o.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
{"row": 14, "col":0, "size_x":18, "size_y":6}
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
    [[WHERE m.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
      [[AND o.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
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
{"row": 20, "col":0, "size_x":18, "size_y":8}
```

---

### Section: Profitable ROAS Analysis

#### 📝 Text: Profitable ROAS Heading

Profitable ROAS — loi nhuan thuc te tren tung dong chi phi marketing

```json metabase-pos
{"row": 28, "col":0, "size_x":18, "size_y":1}
```

#### Question: Profitable ROAS by Channel

Table — channel, spend, revenue, ROAS, margin %, profitable_roas vs prior 30 days.

*Attribution: channel-level join. CAC/payback analysis pending.*

```sql
-- Current 30-day window
WITH current_window AS (
    SELECT
        (current_date - INTERVAL '30 days')::DATE AS period_start,
        (current_date - INTERVAL '1 day')::DATE   AS period_end
),
prior_window AS (
    SELECT
        (current_date - INTERVAL '60 days')::DATE AS period_start,
        (current_date - INTERVAL '31 days')::DATE AS period_end
),

-- Current period spend
current_spend AS (
    SELECT
        m.channel_key,
        SUM(m.spend_amount) AS spend
    FROM fact_marketing_spend m, current_window w
    WHERE m.date_key BETWEEN CAST(strftime(w.period_start, '%Y%m%d') AS INTEGER)
                         AND CAST(strftime(w.period_end,   '%Y%m%d') AS INTEGER)
    GROUP BY m.channel_key
),

-- Current period economics (completed orders only)
current_econ AS (
    SELECT
        e.channel_key,
        SUM(e.net_revenue)   AS revenue,
        SUM(e.gross_profit)  AS gross_profit
    FROM fact_order_economics e, current_window w
    WHERE e.status = 'COMPLETED'
      AND e.date_key BETWEEN CAST(strftime(w.period_start, '%Y%m%d') AS INTEGER)
                         AND CAST(strftime(w.period_end,   '%Y%m%d') AS INTEGER)
    GROUP BY e.channel_key
),

-- Prior period spend
prior_spend AS (
    SELECT
        m.channel_key,
        SUM(m.spend_amount) AS spend
    FROM fact_marketing_spend m, prior_window w
    WHERE m.date_key BETWEEN CAST(strftime(w.period_start, '%Y%m%d') AS INTEGER)
                         AND CAST(strftime(w.period_end,   '%Y%m%d') AS INTEGER)
    GROUP BY m.channel_key
),

-- Prior period economics
prior_econ AS (
    SELECT
        e.channel_key,
        SUM(e.net_revenue)  AS revenue,
        SUM(e.gross_profit) AS gross_profit
    FROM fact_order_economics e, prior_window w
    WHERE e.status = 'COMPLETED'
      AND e.date_key BETWEEN CAST(strftime(w.period_start, '%Y%m%d') AS INTEGER)
                         AND CAST(strftime(w.period_end,   '%Y%m%d') AS INTEGER)
    GROUP BY e.channel_key
)

SELECT
    c.channel_name                                                              AS "Kenh",
    COALESCE(cs.spend, 0)                                                       AS "Chi phi",
    COALESCE(ce.revenue, 0)                                                     AS "Doanh thu",
    -- ROAS = revenue / spend
    ROUND(COALESCE(ce.revenue, 0)::DOUBLE / NULLIF(cs.spend, 0), 2)            AS "ROAS",
    -- Gross Margin % = gross_profit / revenue
    ROUND(
        COALESCE(ce.gross_profit, 0)::DOUBLE / NULLIF(COALESCE(ce.revenue, 0), 0) * 100,
        1
    )                                                                           AS "Bien lai gross (%)",
    -- Profitable ROAS = gross_profit / spend  (= ROAS × margin %)
    ROUND(COALESCE(ce.gross_profit, 0)::DOUBLE / NULLIF(cs.spend, 0), 2)       AS "Profitable ROAS",
    -- Prior period profitable ROAS
    ROUND(COALESCE(pe.gross_profit, 0)::DOUBLE / NULLIF(ps.spend, 0), 2)       AS "Profitable ROAS (30 ngay truoc)",
    -- Delta = current - prior
    ROUND(
        COALESCE(ce.gross_profit, 0)::DOUBLE / NULLIF(cs.spend, 0)
        - COALESCE(pe.gross_profit, 0)::DOUBLE / NULLIF(ps.spend, 0),
        2
    )                                                                           AS "Delta"
FROM current_spend cs
JOIN dim_channels c USING (channel_key)
LEFT JOIN current_econ ce USING (channel_key)
LEFT JOIN prior_spend   ps USING (channel_key)
LEFT JOIN prior_econ    pe USING (channel_key)
WHERE COALESCE(cs.spend, 0) > 0
ORDER BY "Profitable ROAS" DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_height": "compact",
    "table.column_formatting": [
      {
        "columns": ["Profitable ROAS"],
        "type": "single",
        "operator": "<",
        "value": 1,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Profitable ROAS"],
        "type": "single",
        "operator": ">=",
        "value": 2,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Delta"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Chi phi":   { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Bien lai gross (%)": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{"row": 29, "col":0, "size_x":18, "size_y":8}
```

#### Question: Channel ROI Quadrant (Optional)

Scatter — X = ROAS, Y = Bien lai gross (%), bubble size = Chi phi. Phat hien kenh ROAS cao nhung bien lai thap.

*Attribution: channel-level join. CAC/payback analysis pending.*

```sql
WITH current_window AS (
    SELECT
        (current_date - INTERVAL '30 days')::DATE AS period_start,
        (current_date - INTERVAL '1 day')::DATE   AS period_end
),

channel_spend AS (
    SELECT
        m.channel_key,
        SUM(m.spend_amount) AS spend
    FROM fact_marketing_spend m, current_window w
    WHERE m.date_key BETWEEN CAST(strftime(w.period_start, '%Y%m%d') AS INTEGER)
                         AND CAST(strftime(w.period_end,   '%Y%m%d') AS INTEGER)
    GROUP BY m.channel_key
),

channel_econ AS (
    SELECT
        e.channel_key,
        SUM(e.net_revenue)  AS revenue,
        SUM(e.gross_profit) AS gross_profit
    FROM fact_order_economics e, current_window w
    WHERE e.status = 'COMPLETED'
      AND e.date_key BETWEEN CAST(strftime(w.period_start, '%Y%m%d') AS INTEGER)
                         AND CAST(strftime(w.period_end,   '%Y%m%d') AS INTEGER)
    GROUP BY e.channel_key
)

SELECT
    c.channel_name                                                              AS "Kenh",
    ROUND(COALESCE(ce.revenue, 0)::DOUBLE / NULLIF(cs.spend, 0), 2)            AS "ROAS",
    ROUND(
        COALESCE(ce.gross_profit, 0)::DOUBLE / NULLIF(COALESCE(ce.revenue, 0), 0) * 100,
        1
    )                                                                           AS "Bien lai gross (%)",
    COALESCE(cs.spend, 0)                                                       AS "Chi phi (bubble)"
FROM channel_spend cs
JOIN dim_channels c USING (channel_key)
LEFT JOIN channel_econ ce USING (channel_key)
WHERE COALESCE(cs.spend, 0) > 0
  AND COALESCE(ce.revenue, 0) > 0
ORDER BY "ROAS" DESC NULLS LAST
```

```json metabase-viz
{
  "display": "scatter",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["ROAS", "Bien lai gross (%)"],
    "scatter.bubble": "Chi phi (bubble)",
    "graph.x_axis.title_text": "ROAS (Doanh thu / Chi phi)",
    "graph.y_axis.title_text": "Bien lai gross (%)",
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{"row": 37, "col":0, "size_x":18, "size_y":8}
```

#### 📝 Text: Source & Freshness

**Source:** fact_marketing_spend + fact_order_economics · **Cadence:** rolling-30d · **Scope:** customer_type='RETAIL'
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


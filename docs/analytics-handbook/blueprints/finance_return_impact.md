# Return Impact Analysis [All] Blueprint

> **Database:** Sapo
> **Collection:** Finance
> **Collection ID:** 92
> **Audience:** CEO, CFO, Sales Ops Lead
> **Scope:** All sales channels (is_sales_channel = true)
> **Description:** Audience: CEO/CFO/Sales Ops. Scope: All sales channels. Câu hỏi: Refund liability + return rate trend per channel.
> **Domain:** [Returns & Refund Liability](../domains/finance.md#context-returns--refund-liability)
> **Playbook:** [finance_return_impact.md](../playbooks/finance_return_impact.md)
> **Mart source:** `fact_order_returns` (2026-05-27)

Dashboard theo doi muc do phoi nhiem refund, ty le hoan hang theo kenh, phan tich ly do hoan va xu huong theo ngay. Danh cho CEO/CFO trong cac cuoc hop tai chinh hang thang.

## 📂 Collection: Finance

### 🖥️ Dashboard: Return Impact Analysis [All]

**Description**: Audience: CEO/CFO/Sales Ops. Scope: All sales channels. Câu hỏi: Refund liability + return rate trend per channel.

---

#### Filter: Period

```json metabase-filter
{
  "slug": "return_date",
  "type": "date/all-options",
  "default": "thismonth",
  "field_id": 468,
  "field_id_map": {
    "fact_order_returns": 468,
    "int_return_sku_lines": 512
  }
}
```

#### Filter: Channel

```json metabase-filter
{
  "slug": "channel",
  "type": "string/=",
  "field_id": 179
}
```

---

### 📑 Tab: KPI Overview

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
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


#### 📝 Text: Return Overview Heading

Refund liability va ty le hoan hang — muc do rui ro tai chinh ky nay

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Return Rate MTD

Ty le hoan hang thang nay — so don hang hoan / tong don hang hop le cung ky. Alert neu > 5%.

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
),
returns_period AS (
    SELECT COUNT(DISTINCT order_code) AS returned_orders
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
),
orders_period AS (
    SELECT COUNT(DISTINCT o.order_code) AS total_orders
    FROM fact_orders o, filter_bounds
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.ordered_at::DATE >= filter_bounds.p_start
      AND o.ordered_at::DATE <= filter_bounds.p_end
)
SELECT
    ROUND(COALESCE(r.returned_orders, 0) * 100.0 / NULLIF(o.total_orders, 0), 2) AS "Ty le hoan %"
FROM returns_period r, orders_period o
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Ty le hoan %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 2
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":4, "size_y":3}
```

#### ❓ Question: Refund Liability MTD

Tong gia tri hoan tien thang nay — phoi nhiem tai chinh truc tiep.

```sql
SELECT
    COALESCE(SUM(refund_amount), 0) AS "Refund Liability"
FROM fact_order_returns
WHERE 1=1
  [[AND {{return_date}}]]
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Refund Liability": {
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
{"row": 3, "col":4, "size_x":5, "size_y":3}
```

#### ❓ Question: Days-to-Return Histogram (KPI)

Phan phoi lag ngay hoang tra — routing quyet dinh: 0-3d → QC, 4-14d → CS, >30d → fraud review.
Stack by top-3 return reasons. Thay the scalar trung binh vi trung binh khong co y nghia khi phan phoi lech.

```sql
WITH lag_data AS (
    SELECT
        COALESCE(fact_order_returns.return_reason, 'Khong ro') AS return_reason,
        date_diff('day', DATE(fact_orders.ordered_at), fact_order_returns.return_date) AS lag_days
    FROM fact_order_returns
    JOIN fact_orders ON fact_order_returns.order_code = fact_orders.order_code
    WHERE fact_orders.status NOT IN ('CANCELLED', 'Voided')
      [[AND {{return_date}}]]
      AND date_diff('day', DATE(fact_orders.ordered_at), fact_order_returns.return_date) >= 0
),
top_reasons AS (
    SELECT return_reason
    FROM lag_data
    GROUP BY 1
    ORDER BY COUNT(*) DESC
    LIMIT 3
),
bucketed AS (
    SELECT
        CASE
            WHEN lag_days <= 3  THEN '0-3 ngay (QC)'
            WHEN lag_days <= 7  THEN '4-7 ngay'
            WHEN lag_days <= 14 THEN '8-14 ngay (CS)'
            WHEN lag_days <= 30 THEN '15-30 ngay'
            ELSE '>30 ngay (Fraud?)'
        END                                           AS "Bucket ngay hoan",
        CASE
            WHEN l.return_reason IN (SELECT return_reason FROM top_reasons)
            THEN l.return_reason
            ELSE 'Khac'
        END                                           AS "Ly do hoan",
        COUNT(*)                                      AS "So don"
    FROM lag_data l
    GROUP BY 1, 2
)
SELECT "Bucket ngay hoan", "Ly do hoan", "So don"
FROM bucketed
ORDER BY
    CASE "Bucket ngay hoan"
        WHEN '0-3 ngay (QC)'     THEN 1
        WHEN '4-7 ngay'          THEN 2
        WHEN '8-14 ngay (CS)'    THEN 3
        WHEN '15-30 ngay'        THEN 4
        ELSE 5
    END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Bucket ngay hoan", "Ly do hoan"],
    "graph.metrics": ["So don"],
    "stackable.stack_type": "stacked",
    "graph.colors": ["#509EE3", "#88BF4D", "#F2A86F", "#EF8C8C"],
    "graph.x_axis.title_text": "Lag bucket (ngay)",
    "graph.y_axis.title_text": "So don hoan"
  }
}
```

```json metabase-pos
{"row": 3, "col":13, "size_x":5, "size_y":5}
```

#### ❓ Question: Top Return Reason MTD

Ly do hoan pho bien nhat thang nay theo so luong.

```sql
SELECT
    COALESCE(return_reason, 'Khong ro') AS "Ly do hoan #1"
FROM fact_order_returns
WHERE 1=1
  [[AND {{return_date}}]]
GROUP BY 1
ORDER BY COUNT(*) DESC
LIMIT 1
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":9, "size_x":4, "size_y":3}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_returns + fact_orders · **Cadence:** rolling-90d · **Scope:** is_sales_channel=true · **Caveats:** Return events, refund recognition
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Channel Analysis

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
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


#### 📝 Text: Channel Return Heading

Ty le hoan theo kenh ban — kenh nao co muc do hoan bat thuong?

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Return Rate by Channel

Horizontal bar — ty le hoan % theo kenh, sort DESC. Highlight do > 5% (alert threshold). Chi tinh is_sales_channel = true.

```sql
WITH ret AS (
    SELECT
        channel_key,
        COUNT(DISTINCT order_code) AS returned_orders
    FROM fact_order_returns
    [[WHERE {{return_date}}]]
    GROUP BY 1
),
ord AS (
    SELECT
        o.channel_key,
        COUNT(DISTINCT o.order_code) AS total_orders
    FROM fact_orders o
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1
)
SELECT
    dim_channels.channel_name                                             AS "Kenh ban hang",
    COALESCE(ret.returned_orders, 0)                                      AS "Don hoan",
    COALESCE(ord.total_orders, 0)                                         AS "Tong don",
    ROUND(
        COALESCE(ret.returned_orders, 0) * 100.0 / NULLIF(ord.total_orders, 0),
        2
    )                                                                     AS "Ty le hoan %"
FROM ord
LEFT JOIN ret USING (channel_key)
JOIN dim_channels USING (channel_key)
WHERE dim_channels.is_sales_channel
  [[AND {{channel}}]]
ORDER BY "Ty le hoan %" DESC NULLS LAST
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh ban hang"],
    "graph.metrics": ["Ty le hoan %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Ty le hoan (%)",
    "column_settings": {
      "Ty le hoan %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 2
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Ty le hoan %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{"row": 3, "col":0, "size_x":18, "size_y":8}
```

#### 📝 Text: Channel Table Heading

Chi tiet so lieu hoan hang theo kenh

```json metabase-pos
{"row": 11, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Channel Return Detail Table

Table — chi tiet so don hoan, gia tri hoan, ty le hoan per channel, sort by revenue impact DESC.

```sql
WITH ret AS (
    SELECT
        channel_key,
        COUNT(DISTINCT order_code)   AS returned_orders,
        COALESCE(SUM(refund_amount), 0) AS refund_total
    FROM fact_order_returns
    [[WHERE {{return_date}}]]
    GROUP BY 1
),
ord AS (
    SELECT
        o.channel_key,
        COUNT(DISTINCT o.order_code)   AS total_orders
    FROM fact_orders o
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1
)
SELECT
    c.channel_name                                                             AS "Kenh",
    COALESCE(ret.returned_orders, 0)                                           AS "Don hoan",
    COALESCE(ord.total_orders, 0)                                              AS "Tong don",
    ROUND(
        COALESCE(ret.returned_orders, 0) * 100.0 / NULLIF(ord.total_orders, 0),
        2
    )                                                                          AS "Ty le hoan %",
    COALESCE(ret.refund_total, 0)                                              AS "Gia tri hoan (VND)"
FROM ord
LEFT JOIN ret USING (channel_key)
JOIN dim_channels c USING (channel_key)
WHERE c.is_sales_channel
ORDER BY "Gia tri hoan (VND)" DESC NULLS LAST
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Ty le hoan %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Gia tri hoan (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Ty le hoan %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 2
      }
    }
  }
}
```

```json metabase-pos
{"row": 12, "col":0, "size_x":18, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_returns + fact_orders · **Cadence:** rolling-90d · **Scope:** is_sales_channel=true · **Caveats:** Return events, refund recognition
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Return Reasons

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
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


#### 📝 Text: Reason Heading

Phan tich ly do hoan — nguyen nhan nao gay mat doanh thu nhieu nhat?

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Top 10 Return Reasons by Revenue Impact

Horizontal bar — top 10 ly do hoan theo tong gia tri hoan tien, sort DESC.

```sql
SELECT
    COALESCE(return_reason, 'Khong ro')  AS "Ly do hoan",
    COUNT(*)                              AS "So luong hoan",
    COALESCE(SUM(refund_amount), 0)       AS "Gia tri hoan (VND)"
FROM fact_order_returns
WHERE 1=1
  [[AND {{return_date}}]]
GROUP BY 1
ORDER BY "Gia tri hoan (VND)" DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Ly do hoan"],
    "graph.metrics": ["Gia tri hoan (VND)"],
    "graph.colors": ["#EF8C8C"],
    "graph.x_axis.title_text": "Gia tri hoan (VND)",
    "column_settings": {
      "Gia tri hoan (VND)": {
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
{"row": 3, "col":0, "size_x":10, "size_y":8}
```

#### ❓ Question: Return Reason by Volume

Bar chart — so luong hoan theo ly do, sort DESC. Biet ly do nao xay ra nhieu nhat (volume vs value co the khac nhau).

```sql
SELECT
    COALESCE(return_reason, 'Khong ro') AS "Ly do hoan",
    COUNT(*)                             AS "So luong hoan"
FROM fact_order_returns
WHERE 1=1
  [[AND {{return_date}}]]
GROUP BY 1
ORDER BY "So luong hoan" DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Ly do hoan"],
    "graph.metrics": ["So luong hoan"],
    "graph.colors": ["#F2A86F"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "So luong"
  }
}
```

```json metabase-pos
{"row": 3, "col":10, "size_x":8, "size_y":8}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_returns + fact_orders · **Cadence:** rolling-90d · **Scope:** is_sales_channel=true · **Caveats:** Return events, refund recognition
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Cohort & Trend

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
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


#### 📝 Text: Trend Heading

Xu huong hoan hang 90 ngay qua va phan bo lag giua dat hang va hoan

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Daily Return Count Last 90 Days

Line chart — so don hoan moi ngay trong 90 ngay gan nhat. Phat hien spike bat thuong.

```sql
SELECT
    return_date                      AS "Ngay",
    COUNT(*)                         AS "So don hoan",
    COALESCE(SUM(refund_amount), 0)  AS "Gia tri hoan (VND)"
FROM fact_order_returns
WHERE 1=1
  [[AND {{return_date}}]]
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["So don hoan", "Gia tri hoan (VND)"],
    "series_settings": {
      "So don hoan": {
        "display": "line",
        "color": "#EF8C8C",
        "axis": "left"
      },
      "Gia tri hoan (VND)": {
        "display": "line",
        "color": "#F9D45C",
        "axis": "right"
      }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "So don hoan",
    "column_settings": {
      "Gia tri hoan (VND)": {
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
{"row": 3, "col":0, "size_x":18, "size_y":6}
```

#### 📝 Text: Cohort Heading

Cohort: lag phan phoi giua thang dat hang va thang hoan (order_month x return_month)

```json metabase-pos
{"row": 9, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Return Lag Cohort Table

Table — return rate phan ra theo order_month (row) x return_month (col). Cho biet hang hoan chua bao lau sau khi dat. Join fact_orders de lay order_month. Data co the rong neu fact_order_returns moi co.

```sql
WITH cohort AS (
    SELECT
        date_trunc('month', DATE(o.ordered_at))  AS order_month,
        date_trunc('month', r.return_date)            AS return_month,
        COUNT(DISTINCT r.order_code)                  AS returned_orders
    FROM fact_order_returns r
    JOIN fact_orders o ON r.order_code = o.order_code
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND r.return_date >= (current_date - INTERVAL '12 months')
    GROUP BY 1, 2
),
order_totals AS (
    SELECT
        date_trunc('month', ordered_at) AS order_month,
        COUNT(DISTINCT order_code)           AS total_orders
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND ordered_at >= (current_date - INTERVAL '12 months')
    GROUP BY 1
)
SELECT
    STRFTIME(c.order_month::DATE, '%Y-%m') AS "Order Month",
    STRFTIME(c.return_month::DATE, '%Y-%m') AS "Return Month",
    c.returned_orders                        AS "Don hoan",
    t.total_orders                           AS "Tong don",
    ROUND(
        c.returned_orders * 100.0 / NULLIF(t.total_orders, 0),
        2
    )                                        AS "Return Rate %"
FROM cohort c
JOIN order_totals t USING (order_month)
ORDER BY c.order_month, c.return_month
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Return Rate %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Return Rate %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 2
      }
    }
  }
}
```

```json metabase-pos
{"row": 10, "col":0, "size_x":18, "size_y":8}
```

#### 📝 Text: Source & Freshness

**Source:** fact_order_returns + fact_orders · **Cadence:** rolling-90d · **Scope:** is_sales_channel=true · **Caveats:** Return events, refund recognition
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: Return-prone SKUs

> **CAVEAT (IMPORTANT):** Sapo's return API is order-level only — no per-line-item breakdown.
> All SKUs in a returned order appear here. `int_return_sku_lines` allocates refund proportionally
> by line revenue share. Use for triage / ranking direction — not precise per-SKU accounting.
> Source: `int_return_sku_lines` JOIN `dim_products`.

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
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

#### 📝 Text: SKU Return Heading

Top SKU co gia tri hoan tien cao nhat (MTD) — uu tien dam phan nha cung cap va review chat luong

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Top 20 SKUs by Refund Amount (MTD)

Table — top 20 SKU co tong gia tri hoan cao nhat thang nay. Sort by refund DESC.
Du lieu tu int_return_sku_lines (phan bo ty le theo revenue). Flag do khi refund > 5M VND.

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
)
SELECT
    dp.sku                                                         AS "SKU",
    dp.product_name                                                AS "Ten san pham",
    COUNT(DISTINCT rs.return_id)                                   AS "So lan hoan",
    ROUND(SUM(rs.refund_amount_allocated), 0)                      AS "Refund (VND)"
FROM int_return_sku_lines rs
JOIN dim_products dp ON rs.product_key = dp.product_key
CROSS JOIN filter_bounds
WHERE rs.return_date >= filter_bounds.p_start
  AND rs.return_date <= filter_bounds.p_end
  AND dp.sku != 'Unknown'
GROUP BY 1, 2
ORDER BY "Refund (VND)" DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Refund (VND)"],
        "type": "single",
        "operator": ">",
        "value": 5000000,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "Refund (VND)": {
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
{"row": 3, "col":0, "size_x":9, "size_y":9}
```

#### ❓ Question: Top 20 SKUs by Return Rate (MTD)

Table — ty le hoan per SKU = so don hoan / tong don ban cung ky. Flag do khi rate > 3× trung binh danh muc.
Tu so: int_return_sku_lines. Mau so: fact_sales. Min 3 don ban de loc nhieu.

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
),
returns_per_sku AS (
    SELECT
        rs.product_key,
        COUNT(DISTINCT rs.return_id) AS return_count
    FROM int_return_sku_lines rs
    CROSS JOIN filter_bounds
    WHERE rs.return_date >= filter_bounds.p_start
      AND rs.return_date <= filter_bounds.p_end
    GROUP BY 1
),
sold_per_sku AS (
    SELECT
        fs.product_key,
        COUNT(DISTINCT fs.order_id) AS sold_orders
    FROM fact_sales fs
    JOIN fact_orders fo ON fs.order_id = fo.order_id
    CROSS JOIN filter_bounds
    WHERE fo.ordered_at::DATE >= filter_bounds.p_start
      AND fo.ordered_at::DATE <= filter_bounds.p_end
      AND fo.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1
),
portfolio_avg AS (
    SELECT
        ROUND(
            COUNT(DISTINCT r.return_id) * 100.0 / NULLIF(COUNT(DISTINCT fo2.order_id), 0),
            2
        ) AS avg_rate
    FROM fact_order_returns r
    CROSS JOIN filter_bounds
    CROSS JOIN (
        SELECT fo.order_id FROM fact_orders fo
        CROSS JOIN filter_bounds
        WHERE fo.ordered_at::DATE >= filter_bounds.p_start
          AND fo.ordered_at::DATE <= filter_bounds.p_end
          AND fo.status NOT IN ('CANCELLED', 'Voided')
    ) fo2
    WHERE r.return_date >= filter_bounds.p_start
      AND r.return_date <= filter_bounds.p_end
)
SELECT
    dp.sku                                                                     AS "SKU",
    dp.product_name                                                            AS "Ten san pham",
    COALESCE(r.return_count, 0)                                                AS "So lan hoan",
    COALESCE(s.sold_orders, 0)                                                 AS "Don ban",
    ROUND(COALESCE(r.return_count, 0) * 100.0 / NULLIF(s.sold_orders, 0), 2)  AS "Return Rate %",
    pa.avg_rate                                                                AS "TB portfolio %",
    CASE
        WHEN COALESCE(r.return_count, 0) * 100.0 / NULLIF(s.sold_orders, 0)
             > pa.avg_rate * 3
        THEN TRUE ELSE FALSE
    END                                                                        AS "Bat thuong (>3x avg)"
FROM sold_per_sku s
LEFT JOIN returns_per_sku r USING (product_key)
JOIN dim_products dp ON s.product_key = dp.product_key
CROSS JOIN portfolio_avg pa
WHERE dp.sku != 'Unknown'
  AND s.sold_orders >= 3
ORDER BY "Return Rate %" DESC NULLS LAST
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Return Rate %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "Return Rate %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 2
      },
      "TB portfolio %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 2
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":9, "size_x":9, "size_y":9}
```

#### 📝 Text: Reason Matrix Heading

Ma tran: ly do hoan × SKU — SKU nao tap trung nhieu ly do nhat?

```json metabase-pos
{"row": 12, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Return Reason × Top SKUs Matrix

Table — top 15 SKU (by refund) × ly do hoan (count + refund). Phat hien SKU co cu the 1 ly do chiem uu the.

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
),
top_skus AS (
    SELECT rs.product_key
    FROM int_return_sku_lines rs
    CROSS JOIN filter_bounds
    WHERE rs.return_date >= filter_bounds.p_start
      AND rs.return_date <= filter_bounds.p_end
    GROUP BY 1
    ORDER BY SUM(rs.refund_amount_allocated) DESC
    LIMIT 15
)
SELECT
    dp.sku                                             AS "SKU",
    dp.product_name                                    AS "Ten san pham",
    COALESCE(rs.return_reason, 'Khong ro')             AS "Ly do hoan",
    COUNT(DISTINCT rs.return_id)                       AS "So lan hoan",
    ROUND(SUM(rs.refund_amount_allocated), 0)          AS "Refund (VND)"
FROM int_return_sku_lines rs
JOIN dim_products dp ON rs.product_key = dp.product_key
CROSS JOIN filter_bounds
WHERE rs.product_key IN (SELECT product_key FROM top_skus)
  AND rs.return_date >= filter_bounds.p_start
  AND rs.return_date <= filter_bounds.p_end
GROUP BY 1, 2, 3
ORDER BY "Refund (VND)" DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "column_settings": {
      "Refund (VND)": {
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
{"row": 13, "col":0, "size_x":18, "size_y":8}
```

#### 📝 Text: Action Table Heading

Bang hanh dong: SKU → xu huong hoan → khuyen nghi can thiep

```json metabase-pos
{"row": 21, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: SKU Action Table (Prescriptive)

Top 30 SKU (min 3 don ban) voi return rate + ly do chinh → khuyen nghi hanh dong + owner.

```sql
WITH filter_bounds AS (
    SELECT MIN(return_date) AS p_start, MAX(return_date) AS p_end
    FROM fact_order_returns
    WHERE [[AND {{return_date}}]]
),
sku_rates AS (
    SELECT
        rs.product_key,
        COUNT(DISTINCT rs.return_id)                                               AS return_count,
        ROUND(SUM(rs.refund_amount_allocated), 0)                                  AS total_refund,
        MODE() WITHIN GROUP (ORDER BY COALESCE(rs.return_reason, 'Khong ro'))      AS top_reason
    FROM int_return_sku_lines rs
    CROSS JOIN filter_bounds
    WHERE rs.return_date >= filter_bounds.p_start
      AND rs.return_date <= filter_bounds.p_end
    GROUP BY 1
),
sold_cnt AS (
    SELECT
        fs.product_key,
        COUNT(DISTINCT fs.order_id) AS sold_orders
    FROM fact_sales fs
    JOIN fact_orders fo ON fs.order_id = fo.order_id
    CROSS JOIN filter_bounds
    WHERE fo.ordered_at::DATE >= filter_bounds.p_start
      AND fo.ordered_at::DATE <= filter_bounds.p_end
      AND fo.status NOT IN ('CANCELLED', 'Voided')
    GROUP BY 1
)
SELECT
    dp.sku                                                                         AS "SKU",
    dp.product_name                                                                AS "Ten san pham",
    ROUND(sr.return_count * 100.0 / NULLIF(sc.sold_orders, 0), 1)                 AS "Return Rate %",
    sr.top_reason                                                                  AS "Ly do chinh",
    sr.total_refund                                                                AS "Refund (VND)",
    CASE
        WHEN sr.return_count * 100.0 / NULLIF(sc.sold_orders, 0) > 10
             AND LOWER(sr.top_reason) LIKE '%loi%'
            THEN 'QC: Review nha cung cap'
        WHEN sr.return_count * 100.0 / NULLIF(sc.sold_orders, 0) > 5
             AND LOWER(sr.top_reason) LIKE '%size%'
            THEN 'Merch: Cap nhat bang size'
        WHEN sr.return_count * 100.0 / NULLIF(sc.sold_orders, 0) > 5
             AND LOWER(sr.top_reason) LIKE '%sai%'
            THEN 'Ops: Kiem tra quy trinh pick & pack'
        WHEN sr.return_count * 100.0 / NULLIF(sc.sold_orders, 0) > 5
            THEN 'Sales Ops: Dieu tra nguyen nhan'
        ELSE 'Monitor'
    END                                                                            AS "Khuyen nghi",
    CASE
        WHEN sr.return_count * 100.0 / NULLIF(sc.sold_orders, 0) > 10 THEN 'QC / Sourcing'
        WHEN sr.return_count * 100.0 / NULLIF(sc.sold_orders, 0) > 5  THEN 'Sales Ops'
        ELSE '—'
    END                                                                            AS "Owner"
FROM sku_rates sr
JOIN sold_cnt sc ON sr.product_key = sc.product_key
JOIN dim_products dp ON sr.product_key = dp.product_key
WHERE dp.sku != 'Unknown'
  AND sc.sold_orders >= 3
ORDER BY "Return Rate %" DESC NULLS LAST
LIMIT 30
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Return Rate %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Return Rate %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      },
      "Refund (VND)": {
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
{"row": 22, "col":0, "size_x":18, "size_y":8}
```

#### 📝 Text: Source & Freshness (SKU Tab)

**Source:** int_return_sku_lines + dim_products + fact_sales · **Cadence:** MTD · **Caveat:** SKU-return link là xấp xỉ (Sapo API order-level only) — dùng để triage/ranking, không phải kế toán chính xác per-SKU

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


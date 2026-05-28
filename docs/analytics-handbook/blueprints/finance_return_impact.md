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
  "default": "thismonth"
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

### 📑 Tab: KPI Overview

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date), '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y') || ' → ' || strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y') AS " "
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
WITH returns_mtd AS (
    SELECT COUNT(DISTINCT r.order_code) AS returned_orders
    FROM fact_order_returns r
    WHERE r.return_date >= date_trunc('month', current_date)
      AND r.return_date < current_date
),
orders_mtd AS (
    SELECT COUNT(DISTINCT o.order_code) AS total_orders
    FROM fact_orders o
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
      AND o.order_timestamp >= date_trunc('month', current_date)
      AND o.order_timestamp < current_date
)
SELECT
    ROUND(COALESCE(r.returned_orders, 0) * 100.0 / NULLIF(o.total_orders, 0), 2) AS "Ty le hoan %"
FROM returns_mtd r, orders_mtd o
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
WHERE return_date >= date_trunc('month', current_date)
  AND return_date < current_date
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

#### ❓ Question: Avg Days-to-Return MTD

So ngay trung binh tu dat hang den hoan — phat hien van de chat luong (hoan som) hoac gian lan (hoan muon).

```sql
SELECT
    ROUND(AVG(
        date_diff('day', DATE(o.order_timestamp), r.return_date)
    ), 1) AS "Avg Days-to-Return"
FROM fact_order_returns r
JOIN fact_orders o ON r.order_code = o.order_code
WHERE r.return_date >= date_trunc('month', current_date)
  AND r.return_date < current_date
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND date_diff('day', DATE(o.order_timestamp), r.return_date) >= 0
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Avg Days-to-Return": {
        "number_style": "number",
        "decimals": 1,
        "suffix": " ngay"
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":9, "size_x":4, "size_y":3}
```

#### ❓ Question: Top Return Reason MTD

Ly do hoan pho bien nhat thang nay theo so luong.

```sql
SELECT
    COALESCE(return_reason, 'Khong ro') AS "Ly do hoan #1"
FROM fact_order_returns
WHERE return_date >= date_trunc('month', current_date)
  AND return_date < current_date
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
{"row": 3, "col":13, "size_x":5, "size_y":3}
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
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date), '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y') || ' → ' || strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y') AS " "
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
        r.channel_key,
        COUNT(DISTINCT r.order_code) AS returned_orders
    FROM fact_order_returns r
    [[WHERE r.return_date >= {{return_date}}]]
    GROUP BY 1
),
ord AS (
    SELECT
        o.channel_key,
        COUNT(DISTINCT o.order_code) AS total_orders
    FROM fact_orders o
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
    [[AND o.order_timestamp >= {{return_date}}]]
    GROUP BY 1
)
SELECT
    c.channel_name                                                        AS "Kenh ban hang",
    COALESCE(ret.returned_orders, 0)                                      AS "Don hoan",
    COALESCE(ord.total_orders, 0)                                         AS "Tong don",
    ROUND(
        COALESCE(ret.returned_orders, 0) * 100.0 / NULLIF(ord.total_orders, 0),
        2
    )                                                                     AS "Ty le hoan %"
FROM ord
LEFT JOIN ret USING (channel_key)
JOIN dim_channels c USING (channel_key)
WHERE c.is_sales_channel
  [[AND c.channel_name = {{channel}}]]
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
        r.channel_key,
        COUNT(DISTINCT r.order_code)   AS returned_orders,
        COALESCE(SUM(r.refund_amount), 0) AS refund_total
    FROM fact_order_returns r
    [[WHERE r.return_date >= {{return_date}}]]
    GROUP BY 1
),
ord AS (
    SELECT
        o.channel_key,
        COUNT(DISTINCT o.order_code)   AS total_orders
    FROM fact_orders o
    WHERE o.status NOT IN ('CANCELLED', 'Voided')
    [[AND o.order_timestamp >= {{return_date}}]]
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
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date), '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y') || ' → ' || strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y') AS " "
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
  [[AND return_date >= {{return_date}}]]
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
  [[AND return_date >= {{return_date}}]]
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
SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date), '%d/%m/%Y') || ' → ' || strftime(current_date, '%d/%m/%Y') || '  ·  Tháng trước: ' || strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y') || ' → ' || strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y') AS " "
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
WHERE return_date >= (current_date - INTERVAL '90 days')
  AND return_date < current_date
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
        date_trunc('month', DATE(o.order_timestamp))  AS order_month,
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
        date_trunc('month', order_timestamp) AS order_month,
        COUNT(DISTINCT order_code)           AS total_orders
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      AND order_timestamp >= (current_date - INTERVAL '12 months')
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


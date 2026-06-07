---
primary_scope: scope_retail
scope_indicator: "[Retail]"
layer: L2
uses_concepts: [scope_retail, net_revenue, discount_rate, discount_amount, aov]
---

# 📘 Blueprint: Sales Promotion & Discount Analysis [Retail]

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_retail` · Layer L2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
> **Why:** **Promotion analysis MUST use scope_retail.** B2B discount = fixed wholesale price (40–50%), not a promotion. Mixing B2B and retail makes discount rate ~35% vs actual retail 15% — completely misleading.
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`discount_rate`](../semantic/metrics.md#discount_rate) · [`discount_amount`](../semantic/metrics.md#discount_amount) · [`aov`](../semantic/metrics.md#aov)
## 📂 Collection: Marketing & Customers

Promotion analysis, discount tracking for retail customers only.

> **Database:** Sapo

<!-- Filters removed: date/all-options and string/= types don't work with native SQL template tags in DuckDB.
     Date scoping is hardcoded in each SQL (last 30 days). -->

---

### 🖥️ Dashboard: Promotion Analysis [Retail]

**Description**: Phan tich khuyen mai & chiet khau cho **retail customers** — 5 tabs: Tong quan chiet khau, Hieu suat khuyen mai, Phan tich kenh & chi tiet, Discount ROI, Phat hien lam dung & Bat thuong. MoM comparison (30 days vs previous 30 days). Loai bo don CANCELLED va non-retail orders.

---

### 📑 Tab: Tong quan chiet khau

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

#### 📝 Text: Kiểm soát chi phí chiết khấu — có vượt ngưỡng và đang tăng hay giảm?

## Kiểm soát chi phí chiết khấu — có vượt ngưỡng và đang tăng hay giảm?

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Total Discount Amount

Tong tien chiet khau ky nay voi MoM comparison. **Scope: Retail only — loai tru gia si B2B.**

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(o.discount_amount), 0) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
prev_period AS (
    SELECT COALESCE(SUM(o.discount_amount), 0) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "Tong CK",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tong CK": {
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
{"row": 3, "col":0, "size_x":6, "size_y":4}
```

#### ❓ Question: Discount Rate %

Ty le chiet khau / GMV voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT
        CASE WHEN SUM(o.gross_revenue) = 0 THEN 0
             ELSE ROUND(SUM(o.discount_amount) * 100.0 / SUM(o.gross_revenue), 1) END as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
prev_period AS (
    SELECT
        CASE WHEN SUM(o.gross_revenue) = 0 THEN 0
             ELSE ROUND(SUM(o.discount_amount) * 100.0 / SUM(o.gross_revenue), 1) END as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "Ty le CK %",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Ty le CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":6, "size_x":4, "size_y":4}
```

#### ❓ Question: Discount Frequency %

Phan tram don hang co chiet khau voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) * 100.0
                        / COUNT(DISTINCT o.order_id), 1) END as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) * 100.0
                        / COUNT(DISTINCT o.order_id), 1) END as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "Tan suat CK %",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Tan suat CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{"row": 3, "col":10, "size_x":4, "size_y":4}
```

#### ❓ Question: Discounted Orders

So don hang co chiet khau voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
prev_period AS (
    SELECT COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "Don co CK",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{"row": 3, "col":14, "size_x":4, "size_y":4}
```

#### 📝 Text: So sánh Promo vs Non-Promo — khuyến mãi có uplift AOV?

## So sánh Promo vs Non-Promo — khuyến mãi có uplift AOV?

```json metabase-pos
{"row": 7, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Promo vs Non-Promo Summary

So sanh Revenue, Orders, AOV giua Promo va Non-Promo — grouped bar.

```sql
WITH base AS (
    SELECT
        CASE WHEN o.discount_amount > 0 THEN 'Promo' ELSE 'Non-Promo' END as segment,
        o.net_revenue,
        o.order_id
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
)
SELECT
    'Revenue' as "Metric",
    SUM(CASE WHEN segment = 'Promo' THEN net_revenue ELSE 0 END) as "Promo",
    SUM(CASE WHEN segment = 'Non-Promo' THEN net_revenue ELSE 0 END) as "Non-Promo"
FROM base
UNION ALL
SELECT
    'Orders' as "Metric",
    COUNT(DISTINCT CASE WHEN segment = 'Promo' THEN order_id END),
    COUNT(DISTINCT CASE WHEN segment = 'Non-Promo' THEN order_id END)
FROM base
UNION ALL
SELECT
    'AOV' as "Metric",
    CASE WHEN COUNT(DISTINCT CASE WHEN segment = 'Promo' THEN order_id END) = 0 THEN 0
         ELSE SUM(CASE WHEN segment = 'Promo' THEN net_revenue ELSE 0 END)
              / COUNT(DISTINCT CASE WHEN segment = 'Promo' THEN order_id END) END,
    CASE WHEN COUNT(DISTINCT CASE WHEN segment = 'Non-Promo' THEN order_id END) = 0 THEN 0
         ELSE SUM(CASE WHEN segment = 'Non-Promo' THEN net_revenue ELSE 0 END)
              / COUNT(DISTINCT CASE WHEN segment = 'Non-Promo' THEN order_id END) END
FROM base
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Metric"],
    "graph.metrics": ["Promo", "Non-Promo"],
    "series_settings": {
      "Promo": { "color": "#509EE3" },
      "Non-Promo": { "color": "#88BDE6" }
    },
    "graph.y_axis.title_text": "",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "Promo": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Non-Promo": {
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
{"row": 8, "col":0, "size_x":12, "size_y":6}
```

#### ❓ Question: AOV by Discount Band

<!-- Replaces old AOV Uplift scalar (removed 2026-05-28).
     Rationale: AOV(Promo) vs AOV(Non-Promo) compare is biased by min-spend thresholds built into many
     promos — AOV looks higher just because of eligibility filter, not true lift.
     Fix: AOV by band reveals threshold effect vs genuine lift:
       - Monotonic increase with band → likely just threshold effect, not lift
       - Inverted-U → optimal discount band exists (peak = sweet spot) -->

AOV theo khoang chiet khau (0%, 1-10%, 10-20%, 20-30%, >30%) — bar chart + order count overlay. **Scope: Retail only.**

```sql
SELECT
    CASE
        WHEN o.gross_revenue = 0 OR o.discount_amount = 0              THEN '0% (Khong CK)'
        WHEN o.discount_amount * 1.0 / o.gross_revenue < 0.10          THEN '1-10%'
        WHEN o.discount_amount * 1.0 / o.gross_revenue < 0.20          THEN '10-20%'
        WHEN o.discount_amount * 1.0 / o.gross_revenue < 0.30          THEN '20-30%'
        ELSE '>30%'
    END                                                                 AS "Khoang CK",
    CASE
        WHEN o.gross_revenue = 0 OR o.discount_amount = 0              THEN 0
        WHEN o.discount_amount * 1.0 / o.gross_revenue < 0.10          THEN 1
        WHEN o.discount_amount * 1.0 / o.gross_revenue < 0.20          THEN 2
        WHEN o.discount_amount * 1.0 / o.gross_revenue < 0.30          THEN 3
        ELSE 4
    END                                                                 AS _sort,
    COUNT(DISTINCT o.order_id)                                          AS "So don",
    ROUND(SUM(o.net_revenue) / NULLIF(COUNT(DISTINCT o.order_id), 0), 0) AS "AOV"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
GROUP BY 1, 2
ORDER BY 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Khoang CK"],
    "graph.metrics": ["AOV", "So don"],
    "series_settings": {
      "AOV":    { "display": "bar",  "color": "#509EE3", "axis": "left"  },
      "So don": { "display": "line", "color": "#F9D45C", "axis": "right" }
    },
    "graph.y_axis.title_text": "AOV (VND)",
    "graph.x_axis.title_text": "Khoang chiet khau",
    "graph.x_axis.scale": "ordinal",
    "column_settings": {
      "AOV": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "card.description": "Neu AOV tang monotonic theo band → chi la threshold effect (promo yeu cau chi tieu toi thieu), KHONG phai true lift. Neu AOV dat dinh o band giua → ton tai khoang chiet khau toi uu."
  }
}
```

```json metabase-pos
{"row": 8, "col":12, "size_x":6, "size_y":6}
```

#### 📝 Text: Phân tích độ sâu chiết khấu — phát hiện đơn bất thường > 30%

## Phân tích độ sâu chiết khấu — phát hiện đơn bất thường > 30%

```json metabase-pos
{"row": 14, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Discount Depth Histogram

Phan bo don hang theo % chiet khau (0-10%, 10-20%, 20-30%, 30%+).

```sql
SELECT
    CASE
        WHEN o.gross_revenue = 0 THEN 'N/A'
        WHEN o.discount_amount / o.gross_revenue < 0.1 THEN '0-10%'
        WHEN o.discount_amount / o.gross_revenue < 0.2 THEN '10-20%'
        WHEN o.discount_amount / o.gross_revenue < 0.3 THEN '20-30%'
        ELSE '30%+'
    END as "Muc chiet khau",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND o.discount_amount > 0
GROUP BY 1
ORDER BY
    CASE
        WHEN "Muc chiet khau" = '0-10%' THEN 1
        WHEN "Muc chiet khau" = '10-20%' THEN 2
        WHEN "Muc chiet khau" = '20-30%' THEN 3
        WHEN "Muc chiet khau" = '30%+' THEN 4
        ELSE 5
    END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Muc chiet khau"],
    "graph.metrics": ["So don"],
    "series_settings": {
      "So don": { "color": "#509EE3" }
    },
    "graph.y_axis.title_text": "So don",
    "graph.x_axis.title_text": "",
    "graph.x_axis.scale": "ordinal"
  }
}
```

```json metabase-pos
{"row": 15, "col":0, "size_x":12, "size_y":6}
```

#### ❓ Question: Avg Discount % by Channel

Ranking kenh theo ty le chiet khau trung binh — horizontal bar.

```sql
SELECT
    ch.channel_name as "Kenh",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as "Ty le CK %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND o.discount_amount > 0
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Ty le CK %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Ty le CK %",
    "column_settings": {
      "Ty le CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{"row": 15, "col":12, "size_x":6, "size_y":6}
```

#### 📝 Text: Theo dõi xu hướng chiết khấu — trend amount và rate

## Theo dõi xu hướng chiết khấu — trend amount và rate

```json metabase-pos
{"row": 21, "col":0, "size_x":18, "size_y":1}
```

#### ❓ Question: Discount Amount & Rate Trend

Xu huong tien chiet khau (bar) va ty le CK (line) theo thang — combo chart.

```sql
SELECT
    date_trunc('month', o.ordered_at)::date as "Thang",
    SUM(o.discount_amount) as "Tien CK",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as "Ty le CK %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '6 months'
  AND o.ordered_at < current_date
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["Tien CK", "Ty le CK %"],
    "series_settings": {
      "Tien CK": { "display": "bar", "color": "#509EE3" },
      "Ty le CK %": { "display": "line", "color": "#F9D45C", "line.style": "solid" }
    },
    "graph.y_axis.title_text": "Tien CK (VND)",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "Tien CK": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Ty le CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{"row": 22, "col":0, "size_x":18, "size_y":6}
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_promotions · **Cadence:** rolling-30d · **Scope:** scope_retail (pre-computed) · **Caveats:** Baseline = non-promo same-channel-period
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Hieu suat khuyen mai

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Xác định promotion hiệu quả — ranking doanh thu và usage

## Xác định promotion hiệu quả — ranking doanh thu và usage

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total Promo Revenue

Tong doanh thu tu don co promo voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
prev_period AS (
    SELECT COALESCE(SUM(o.net_revenue), 0) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "DT Promo",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "DT Promo": {
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

#### ❓ Question: Promo Usage Count

Tong so don dung promo voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT COUNT(DISTINCT o.order_id) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
prev_period AS (
    SELECT COUNT(DISTINCT o.order_id) as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "Luot dung",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Unique Promos Active

So chuong trinh khuyen mai dang active — single value (khong co MoM).

```sql
SELECT COUNT(DISTINCT p.promotion_code) as "So CT active"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.scope_retail
  AND o.discount_amount > 0
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND p.promotion_code IS NOT NULL
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Avg Revenue per Promo

Doanh thu trung binh moi chuong trinh voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT p.promotion_code) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT p.promotion_code) END as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      AND p.promotion_code IS NOT NULL
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT p.promotion_code) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT p.promotion_code) END as val
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
      AND p.promotion_code IS NOT NULL
)
SELECT
    tp.val as "DT TB/CT",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "DT TB/CT": {
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
{ "row": 3, "col": 14, "size_x": 4, "size_y": 4 }
```

#### 📝 Text: Review top 10 promotion — doanh thu và lượt sử dụng

## Review top 10 promotion — doanh thu và lượt sử dụng

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top 10 Promotions by Revenue

Ranking chuong trinh khuyen mai theo doanh thu — horizontal bar.

```sql
SELECT
    COALESCE(p.promotion_code, 'Khong ro') as "Ma KM",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.scope_retail
  AND o.discount_amount > 0
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Ma KM"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Doanh thu (VND)",
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
{ "row": 8, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 10 Promotions by Usage

Ranking chuong trinh khuyen mai theo luot su dung — horizontal bar.

```sql
SELECT
    COALESCE(p.promotion_code, 'Khong ro') as "Ma KM",
    COUNT(DISTINCT o.order_id) as "Luot dung"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.scope_retail
  AND o.discount_amount > 0
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Ma KM"],
    "graph.metrics": ["Luot dung"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "Luot su dung"
  }
}
```

```json metabase-pos
{ "row": 8, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Tra cứu chi tiết promotion — code, usage, revenue, discount rate

## Tra cứu chi tiết promotion — code, usage, revenue, discount rate

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Promotion Performance Table

Bang chi tiet hieu suat tung chuong trinh khuyen mai — conditional formatting tren Discount Rate %.

```sql
SELECT
    COALESCE(p.promotion_code, 'Khong ro') as "Ma KM",
    p.promotion_type as "Loai",
    COUNT(DISTINCT o.order_id) as "So don",
    SUM(o.net_revenue) as "Doanh thu",
    SUM(o.discount_amount) as "Tien CK",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as "Ty le CK %",
    CASE WHEN COUNT(DISTINCT o.order_id) = 0 THEN 0
         ELSE ROUND(SUM(o.net_revenue) / COUNT(DISTINCT o.order_id), 0) END as "AOV"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.scope_retail
  AND o.discount_amount > 0
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
GROUP BY 1, 2
ORDER BY "Doanh thu" DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Ty le CK %"],
        "type": "single",
        "operator": ">=",
        "value": 20,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Ty le CK %"],
        "type": "single",
        "operator": "<",
        "value": 10,
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
      "Tien CK": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "AOV": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Ty le CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Theo dõi xu hướng sử dụng promotion — top 5 codes

## Theo dõi xu hướng sử dụng promotion — top 5 codes

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Promo Usage Trend

Phan bo luot dung promo theo thang, chia theo top 5 codes — stacked bar.

```sql
WITH top5 AS (
    SELECT p.promotion_code
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '6 months'
      AND o.ordered_at < current_date
      AND p.promotion_code IS NOT NULL
    GROUP BY 1
    ORDER BY COUNT(DISTINCT o.order_id) DESC
    LIMIT 5
)
SELECT
    date_trunc('month', o.ordered_at)::date as "Thang",
    COALESCE(p.promotion_code, 'Khac') as "Ma KM",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.scope_retail
  AND o.discount_amount > 0
  AND o.ordered_at >= current_date - INTERVAL '6 months'
  AND o.ordered_at < current_date
  AND p.promotion_code IN (SELECT promotion_code FROM top5)
GROUP BY 1, 2
ORDER BY 1, 2
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Thang", "Ma KM"],
    "graph.metrics": ["So don"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "So don"
  }
}
```

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_promotions · **Cadence:** rolling-30d · **Scope:** scope_retail (pre-computed) · **Caveats:** Baseline = non-promo same-channel-period
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Phan tich kenh & chi tiet


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Phân tích tác động promo theo kênh — kênh nào phụ thuộc nhiều?

## Phân tích tác động promo theo kênh — kênh nào phụ thuộc nhiều?

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Promo Revenue Share by Channel

Ty le doanh thu promo vs non-promo theo kenh — stacked bar.

```sql
SELECT
    ch.channel_name as "Kenh",
    SUM(CASE WHEN o.discount_amount > 0 THEN o.net_revenue ELSE 0 END) as "DT Promo",
    SUM(CASE WHEN o.discount_amount = 0 THEN o.net_revenue ELSE 0 END) as "DT Non-Promo"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
GROUP BY 1
ORDER BY SUM(o.net_revenue) DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["DT Promo", "DT Non-Promo"],
    "series_settings": {
      "DT Promo": { "color": "#509EE3" },
      "DT Non-Promo": { "color": "#88BDE6" }
    },
    "graph.y_axis.title_text": "Doanh thu (VND)",
    "graph.x_axis.title_text": "",
    "column_settings": {
      "DT Promo": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "DT Non-Promo": {
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
{ "row": 3, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Discount Rate by Channel

Ranking kenh theo ty le chiet khau — horizontal bar.

```sql
SELECT
    ch.channel_name as "Kenh",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as "Ty le CK %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Ty le CK %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Ty le CK %",
    "column_settings": {
      "Ty le CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: So sánh hiệu suất kênh MoM — highlight biến động lớn

## So sánh hiệu suất kênh MoM — highlight biến động lớn

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Promo Performance Table

Bang chi tiet hieu suat khuyen mai theo kenh — conditional formatting tren MoM Change %.

```sql
WITH
this_period AS (
    SELECT
        ch.channel_name as channel,
        COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) as promo_orders,
        SUM(CASE WHEN o.discount_amount > 0 THEN o.net_revenue ELSE 0 END) as promo_revenue,
        SUM(o.discount_amount) as discount_amount,
        ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as discount_rate
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
    GROUP BY 1
),
prev_period AS (
    SELECT
        ch.channel_name as channel,
        SUM(CASE WHEN o.discount_amount > 0 THEN o.net_revenue ELSE 0 END) as promo_revenue
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
    GROUP BY 1
)
SELECT
    tp.channel as "Kenh",
    tp.promo_orders as "Don Promo",
    tp.promo_revenue as "DT Promo",
    tp.discount_amount as "Tien CK",
    tp.discount_rate as "Ty le CK %",
    CASE WHEN pp.promo_revenue IS NULL OR pp.promo_revenue = 0 THEN NULL
         ELSE ROUND((tp.promo_revenue - pp.promo_revenue) * 100.0 / pp.promo_revenue, 1) END as "MoM %"
FROM this_period tp
LEFT JOIN prev_period pp ON tp.channel = pp.channel
ORDER BY tp.promo_revenue DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["MoM %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "DT Promo": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Tien CK": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Ty le CK %": {
        "suffix": "%"
      },
      "MoM %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Điều tra đơn chiết khấu cao — flag đơn > 30% CK để audit

## Điều tra đơn chiết khấu cao — flag đơn > 30% CK để audit

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: High-Discount Orders List

Danh sach don hang co chiet khau > 30% — conditional formatting tren Discount %.

```sql
SELECT
    o.order_code as "Ma don",
    o.ordered_at::date as "Ngay",
    ch.channel_name as "Kenh",
    COALESCE(p.promotion_code, o.discount_codes, '') as "Ma KM",
    o.gross_revenue as "Doanh thu goc",
    o.discount_amount as "Tien CK",
    ROUND(o.discount_amount * 100.0 / NULLIF(o.gross_revenue, 0), 1) as "Ty le CK %",
    o.net_revenue as "Doanh thu thuan"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND o.gross_revenue > 0
  AND o.discount_amount * 1.0 / o.gross_revenue > 0.3
ORDER BY o.discount_amount DESC
LIMIT 100
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Ty le CK %"],
        "type": "single",
        "operator": ">=",
        "value": 30,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "[\"name\",\"Ma don\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/orders/{{Ma don}}"
        }
      },
      "Doanh thu goc": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Tien CK": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Doanh thu thuan": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Ty le CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 9 }
```



#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_promotions · **Cadence:** rolling-30d · **Scope:** scope_retail (pre-computed) · **Caveats:** Baseline = non-promo same-channel-period
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Discount ROI


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

<!-- Discount ROI analysis — incremental revenue vs discount cost per promotion code.
     Baseline proxy: avg net_revenue per order from non-discounted orders in same period + same channel.
     Caveat: ROI estimation only. No holdout group. Baseline = non-promo avg order value × promo order count.
     Limitation: cannot isolate pure uplift without A/B test; treat as directional signal. -->

#### 📝 Text: Discount ROI — đo lường hiệu quả thực của chiết khấu, không chỉ chi phí

## Discount ROI — đo lường hiệu quả thực của chiết khấu, không chỉ chi phí

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_promotions · **Cadence:** rolling-30d · **Scope:** scope_retail (pre-computed) · **Caveats:** Baseline = non-promo same-channel-period
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount ROI by Promotion Code

Bang ROI chiet khau theo ma khuyen mai — so sanh tien chiet khau vs doanh thu tang them (incremental). Baseline: trung binh don hang khong khuyen mai cung ky, cung kenh. **Scope: Retail only.**

```sql
-- Caveat: incremental revenue proxy = (avg non-promo AOV × promo order count) subtracted from actual promo revenue.
-- Limitation: no holdout group; treat as directional signal only.
WITH
period_scope AS (
    SELECT
        o.order_id,
        o.channel_key,
        o.discount_amount,
        o.net_revenue,
        COALESCE(p.promotion_code, 'Khong ro') AS campaign_code
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
-- Baseline: avg net_revenue per non-discounted order per channel (same 30-day window)
channel_baseline AS (
    SELECT
        o.channel_key,
        CASE WHEN COUNT(DISTINCT CASE WHEN o.discount_amount = 0 THEN o.order_id END) = 0
             THEN 0
             ELSE SUM(CASE WHEN o.discount_amount = 0 THEN o.net_revenue ELSE 0 END)
                  / COUNT(DISTINCT CASE WHEN o.discount_amount = 0 THEN o.order_id END)
        END AS baseline_aov
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
    GROUP BY o.channel_key
),
-- Promo aggregates per campaign_code
promo_agg AS (
    SELECT
        ps.campaign_code,
        COUNT(DISTINCT ps.order_id)                              AS promo_orders,
        SUM(ps.discount_amount)                                   AS discount_amount,
        SUM(ps.net_revenue)                                       AS actual_revenue,
        SUM(COALESCE(cb.baseline_aov, 0))                        AS baseline_revenue_sum
    FROM period_scope ps
    LEFT JOIN channel_baseline cb ON ps.channel_key = cb.channel_key
    WHERE ps.discount_amount > 0
    GROUP BY ps.campaign_code
)
SELECT
    campaign_code                                                 AS "Ma KM",
    promo_orders                                                  AS "So don",
    discount_amount                                               AS "Tien CK",
    actual_revenue                                                AS "Doanh thu thuc",
    baseline_revenue_sum                                          AS "Doanh thu baseline",
    (actual_revenue - baseline_revenue_sum)                       AS "Doanh thu tang them",
    CASE
        WHEN discount_amount = 0 THEN NULL
        ELSE ROUND(
            ((actual_revenue - baseline_revenue_sum) - discount_amount)
            * 100.0 / NULLIF(discount_amount, 0),
        1)
    END                                                           AS "ROI %"
FROM promo_agg
ORDER BY "ROI %" DESC NULLS LAST
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["ROI %"],
        "type": "single",
        "operator": ">=",
        "value": 200,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["ROI %"],
        "type": "single",
        "operator": "<",
        "value": -50,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "Tien CK": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Doanh thu thuc": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Doanh thu baseline": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Doanh thu tang them": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "ROI %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Xu hướng ROI chiết khấu theo tháng — phát hiện chiến dịch hiệu quả tăng/giảm

## Xu hướng ROI chiết khấu theo tháng — phát hiện chiến dịch hiệu quả tăng/giảm

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount ROI Trend (Monthly)

Xu huong ROI chiet khau toan bo (aggregate) theo thang — line chart. 6 thang gan nhat. **Scope: Retail only.**

```sql
-- Monthly aggregate ROI: (incremental_revenue - discount_cost) / discount_cost
-- Baseline: non-promo avg AOV × promo order count per month, per channel
WITH
monthly_baseline AS (
    SELECT
        date_trunc('month', o.ordered_at)::date AS thang,
        o.channel_key,
        CASE WHEN COUNT(DISTINCT CASE WHEN o.discount_amount = 0 THEN o.order_id END) = 0
             THEN 0
             ELSE SUM(CASE WHEN o.discount_amount = 0 THEN o.net_revenue ELSE 0 END)
                  / COUNT(DISTINCT CASE WHEN o.discount_amount = 0 THEN o.order_id END)
        END AS baseline_aov
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.ordered_at >= current_date - INTERVAL '6 months'
      AND o.ordered_at < current_date
    GROUP BY 1, 2
),
monthly_promo AS (
    SELECT
        date_trunc('month', o.ordered_at)::date AS thang,
        o.channel_key,
        SUM(o.discount_amount)                                    AS total_discount,
        SUM(o.net_revenue)                                        AS total_actual_revenue,
        COUNT(DISTINCT o.order_id)                                AS promo_orders
    FROM fact_orders o
    JOIN dim_customers c ON o.customer_key = c.customer_key
    WHERE o.scope_retail
      AND o.discount_amount > 0
      AND o.ordered_at >= current_date - INTERVAL '6 months'
      AND o.ordered_at < current_date
    GROUP BY 1, 2
),
monthly_combined AS (
    SELECT
        mp.thang,
        SUM(mp.total_discount)                                    AS total_discount,
        SUM(mp.total_actual_revenue)                              AS total_actual,
        SUM(mb.baseline_aov * mp.promo_orders)                    AS total_baseline
    FROM monthly_promo mp
    LEFT JOIN monthly_baseline mb ON mp.thang = mb.thang AND mp.channel_key = mb.channel_key
    GROUP BY mp.thang
)
SELECT
    thang                                                         AS "Thang",
    CASE WHEN total_discount = 0 THEN NULL
         ELSE ROUND(
             ((total_actual - total_baseline) - total_discount)
             * 100.0 / NULLIF(total_discount, 0),
         1)
    END                                                           AS "ROI %"
FROM monthly_combined
ORDER BY thang
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["ROI %"],
    "series_settings": {
      "ROI %": { "color": "#509EE3", "line.style": "solid" }
    },
    "graph.y_axis.title_text": "ROI %",
    "graph.x_axis.title_text": "",
    "graph.show_goal": true,
    "graph.goal_value": 0,
    "graph.goal_label": "Breakeven",
    "column_settings": {
      "ROI %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Phân tích cannibalization — chiết khấu có tạo ra doanh thu thật hay chỉ dịch chuyển?

## Phân tích cannibalization — chiết khấu có tạo ra doanh thu thật hay chỉ dịch chuyển?

> **Caveat:** Category-level proxy; SKU-level cannibalization needs further analysis. Signal: if non-promo categories drop ≈ promo categories gain → consumers shifted, no incremental lift.

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Cannibalization by Product Type

So sanh units_sold ky khuyen mai vs ky truoc cho tung loai san pham (chia theo co hay khong co don khuyen mai). **Scope: Retail only.** Dung `fact_sales` de co cap do san pham.

```sql
-- Cannibalization proxy: compare units sold per product_type in promo period vs prior period.
-- "Has promo" = product_type appeared in orders with discount_amount > 0 in current period.
-- If non-promo types drop by ~same amount as promo types gain → demand shifted, not incremental.
WITH
promo_period AS (
    SELECT
        p.product_type                                                           AS product_type,
        SUM(fs.quantity)                                                         AS units_promo
    FROM fact_sales fs
    JOIN dim_products p ON fs.product_key = p.product_key
    JOIN dim_customers c ON fs.customer_key = c.customer_key
    WHERE fs.ordered_at >= current_date - INTERVAL '30 days'
      AND fs.ordered_at < current_date
      AND fs.scope_retail
    GROUP BY 1
),
prior_period AS (
    SELECT
        p.product_type                                                           AS product_type,
        SUM(fs.quantity)                                                         AS units_prior
    FROM fact_sales fs
    JOIN dim_products p ON fs.product_key = p.product_key
    JOIN dim_customers c ON fs.customer_key = c.customer_key
    WHERE fs.ordered_at >= current_date - INTERVAL '60 days'
      AND fs.ordered_at < current_date - INTERVAL '30 days'
      AND fs.scope_retail
    GROUP BY 1
),
-- Flag which product types had active promo orders in current period
promo_active_types AS (
    SELECT DISTINCT p.product_type
    FROM fact_sales fs
    JOIN dim_products p ON fs.product_key = p.product_key
    JOIN dim_customers c ON fs.customer_key = c.customer_key
    WHERE fs.ordered_at >= current_date - INTERVAL '30 days'
      AND fs.ordered_at < current_date
      AND fs.discount_amount > 0
      AND fs.scope_retail
)
SELECT
    pp.product_type                                                              AS "Loai SP",
    CASE WHEN pat.product_type IS NOT NULL THEN 'Co KM' ELSE 'Khong KM' END     AS "Co khuyen mai?",
    COALESCE(prp.units_prior, 0)                                                 AS "Units ky truoc",
    COALESCE(pp.units_promo, 0)                                                  AS "Units ky nay",
    (COALESCE(pp.units_promo, 0) - COALESCE(prp.units_prior, 0))                AS "Delta units",
    CASE WHEN COALESCE(prp.units_prior, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(pp.units_promo, 0) - COALESCE(prp.units_prior, 0))
                    * 100.0 / prp.units_prior, 1)
    END                                                                          AS "Delta %"
FROM promo_period pp
LEFT JOIN prior_period prp   ON pp.product_type = prp.product_type
LEFT JOIN promo_active_types pat ON pp.product_type = pat.product_type
WHERE pp.product_type IS NOT NULL
ORDER BY CASE WHEN pat.product_type IS NOT NULL THEN 0 ELSE 1 END, pp.units_promo DESC
LIMIT 40
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Delta units"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Delta units"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Delta %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 18, "size_y": 8 }
```

---

### 📑 Tab: Phat hien lam dung & Bat thuong

> **Audience:** Finance + Sales Ops + Sales Manager · **Cadence:** Weekly review · **Scope:** RETAIL only · **Purpose:** Detect voucher abuse, leaked promo codes, staff discount pushing, staff-customer collusion.

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') || '  ·  Review: Hàng tuần với Finance + Sales Ops' AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Tóm tắt rủi ro lạm dụng — đếm các dấu hiệu bất thường

## Tóm tắt rủi ro lạm dụng — đếm các dấu hiệu bất thường

> **Action:** Nếu bất kỳ chỉ số nào > 0 → Finance + Sales Ops review ngay trong tuần.

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Abuse Risk Scorecard

Scorecard tom tat: so KH nghi van, so code bi ro ri, so nhan vien day chiet khau cao, tong VND co rui ro. **Scope: Retail, last 30 days.**

```sql
-- Scorecard: count suspicious customers, leaked codes, high-discount staff, total VND at risk
WITH
suspicious_customers AS (
    SELECT COUNT(*) AS cnt, SUM(total_ck) AS total_vnd
    FROM (
        SELECT c.customer_key,
               SUM(o.discount_amount)                                       AS total_ck,
               COUNT(DISTINCT COALESCE(p.promotion_code, o.discount_codes)) AS distinct_codes,
               COUNT(DISTINCT o.order_id)                                   AS order_count
        FROM fact_orders o
        JOIN dim_customers c ON o.customer_key = c.customer_key
        LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
        WHERE o.scope_retail
          AND o.ordered_at >= current_date - INTERVAL '30 days'
          AND o.ordered_at < current_date
          AND o.discount_amount > 0
        GROUP BY c.customer_key
        HAVING SUM(o.discount_amount) > 5000000 OR COUNT(DISTINCT COALESCE(p.promotion_code, o.discount_codes)) > 5
    ) sub
),
suspicious_codes AS (
    SELECT COUNT(*) AS cnt, SUM(total_ck) AS total_vnd
    FROM (
        SELECT COALESCE(p.promotion_code, o.discount_codes)              AS code,
               COUNT(DISTINCT o.order_id)                                AS total_uses,
               COUNT(DISTINCT o.customer_key)                            AS unique_customers,
               SUM(o.discount_amount)                                    AS total_ck,
               ROUND(COUNT(DISTINCT o.customer_key) * 1.0
                     / NULLIF(COUNT(DISTINCT o.order_id), 0), 3)        AS unique_ratio
        FROM fact_orders o
        JOIN dim_customers c ON o.customer_key = c.customer_key
        LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
        WHERE o.scope_retail
          AND o.ordered_at >= current_date - INTERVAL '30 days'
          AND o.ordered_at < current_date
          AND o.discount_amount > 0
          AND COALESCE(p.promotion_code, o.discount_codes) IS NOT NULL
        GROUP BY 1
        HAVING COUNT(DISTINCT o.order_id) > 10
           AND ROUND(COUNT(DISTINCT o.customer_key) * 1.0 / NULLIF(COUNT(DISTINCT o.order_id), 0), 3) < 0.3
    ) sub
),
suspicious_staff AS (
    SELECT COUNT(*) AS cnt, SUM(total_ck) AS total_vnd
    FROM (
        SELECT o.seller_staff_key,
               COUNT(DISTINCT CASE WHEN o.discount_amount * 1.0 / NULLIF(o.gross_revenue, 0) > 0.3
                                   THEN o.order_id END)                  AS high_ck_orders,
               SUM(o.discount_amount)                                    AS total_ck
        FROM fact_orders o
        JOIN dim_customers c ON o.customer_key = c.customer_key
        WHERE o.scope_retail
          AND o.ordered_at >= current_date - INTERVAL '30 days'
          AND o.ordered_at < current_date
          AND o.seller_staff_key IS NOT NULL
        GROUP BY 1
        HAVING COUNT(DISTINCT CASE WHEN o.discount_amount * 1.0 / NULLIF(o.gross_revenue, 0) > 0.3
                                   THEN o.order_id END) > 5
    ) sub
)
SELECT
    sc.cnt                                AS "KH nghi van",
    sc.total_vnd                          AS "VND rui ro (KH)",
    cd.cnt                                AS "Code bi ro ri",
    cd.total_vnd                          AS "VND rui ro (Code)",
    st.cnt                                AS "NV day CK cao",
    st.total_vnd                          AS "VND rui ro (NV)",
    COALESCE(sc.total_vnd, 0)
      + COALESCE(cd.total_vnd, 0)
      + COALESCE(st.total_vnd, 0)         AS "Tong VND co rui ro"
FROM suspicious_customers sc, suspicious_codes cd, suspicious_staff st
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["KH nghi van", "Code bi ro ri", "NV day CK cao"],
        "type": "single",
        "operator": ">",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "VND rui ro (KH)":   { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "VND rui ro (Code)": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "VND rui ro (NV)":   { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Tong VND co rui ro":{ "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 4 }
```

#### 📝 Text: Top 20 khách hàng sử dụng chiết khấu bất thường — nghi vấn lạm dụng

## Top 20 khách hàng sử dụng chiết khấu bất thường — nghi vấn lạm dụng

> **Flag:** distinct promo codes > 5 HOẶC total_discount > 5M VND trong 30 ngày → highlight đỏ. **Action:** Finance + Sales Ops kiểm tra danh sách hàng tuần.

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top 20 Customers by Discount Usage (Suspicious)

Top 20 khach hang co chiet khau cao nhat 30 ngay — phat hien lam dung. **Scope: Retail only.**

```sql
SELECT
    c.full_name                                                         AS "Ten KH",
    c.phone                                                             AS "So dien thoai",
    SUM(o.discount_amount)                                              AS "Tong CK 30d",
    COUNT(DISTINCT COALESCE(p.promotion_code, o.discount_codes))        AS "So code da dung",
    COUNT(DISTINCT o.order_id)                                          AS "So don",
    CASE WHEN SUM(o.gross_revenue) = 0 THEN 0
         ELSE ROUND(SUM(o.discount_amount) * 100.0 / SUM(o.gross_revenue), 1)
    END                                                                 AS "CK trung binh %",
    CASE
        WHEN SUM(o.discount_amount) > 5000000
          OR COUNT(DISTINCT COALESCE(p.promotion_code, o.discount_codes)) > 5
        THEN 'Nghi van'
        ELSE 'Binh thuong'
    END                                                                 AS "Trang thai"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND o.discount_amount > 0
GROUP BY c.customer_key, c.full_name, c.phone
ORDER BY SUM(o.discount_amount) DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Trang thai"],
        "type": "single",
        "operator": "=",
        "value": "Nghi van",
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "Tong CK 30d": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "CK trung binh %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Promo code bị rò rỉ hoặc chia sẻ — unique-to-uses ratio thấp

## Promo code bị rò rỉ hoặc chia sẻ — unique-to-uses ratio thấp

> **Signal:** unique_ratio = unique_customers / total_uses < 0.3 VÀ total_uses > 10 → code bị share rộng rãi, không còn kiểm soát được. **Action:** Marketing kill/restrict code trong 48h.

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Suspicious Promo Codes (Leaked / Shared)

Bang promo code co ty le unique KH thap — nghi bi ro ri. **Scope: Retail, last 30 days. HAVING: total_uses > 10 AND unique_ratio < 0.3.**

```sql
SELECT
    COALESCE(p.promotion_code, o.discount_codes)                        AS "Ma code",
    COUNT(DISTINCT o.order_id)                                          AS "Tong luot dung",
    COUNT(DISTINCT o.customer_key)                                      AS "KH duy nhat",
    ROUND(COUNT(DISTINCT o.customer_key) * 1.0
          / NULLIF(COUNT(DISTINCT o.order_id), 0), 3)                   AS "Unique ratio",
    SUM(o.discount_amount)                                              AS "Tong CK da cap"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND o.discount_amount > 0
  AND COALESCE(p.promotion_code, o.discount_codes) IS NOT NULL
GROUP BY 1
HAVING COUNT(DISTINCT o.order_id) > 10
   AND ROUND(COUNT(DISTINCT o.customer_key) * 1.0
             / NULLIF(COUNT(DISTINCT o.order_id), 0), 3) < 0.3
ORDER BY SUM(o.discount_amount) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Unique ratio"],
        "type": "single",
        "operator": "<",
        "value": 0.2,
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Unique ratio"],
        "type": "single",
        "operator": ">=",
        "value": 0.2,
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Tong CK da cap": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 7 }
```

#### 📝 Text: Nhân viên đẩy chiết khấu cao — staff discount push leaderboard

## Nhân viên đẩy chiết khấu cao — staff discount push leaderboard

> **Flag:** high_discount_orders > 5 → cam; > 10 → đỏ. **Note:** Chỉ áp dụng cho đơn retail do nhân viên tạo (seller_staff_key). **Action:** Sales Manager review nhân viên flag đỏ.

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Staff Discount Push Leaderboard

Nhan vien co nhieu don chiet khau > 30% nhat — phat hien day chiet khau cao. **Scope: Retail, last 30 days, seller_staff_key not null.**

```sql
SELECT
    COALESCE(s.full_name, o.seller_staff_key)                           AS "Nhan vien",
    COUNT(DISTINCT CASE
        WHEN o.discount_amount * 1.0 / NULLIF(o.gross_revenue, 0) > 0.3
        THEN o.order_id END)                                            AS "Don CK > 30%",
    SUM(o.discount_amount)                                              AS "Tong CK da cap",
    COUNT(DISTINCT o.customer_key)                                      AS "So KH phuc vu",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) AS "CK trung binh %",
    CASE
        WHEN COUNT(DISTINCT CASE WHEN o.discount_amount * 1.0 / NULLIF(o.gross_revenue, 0) > 0.3
                                 THEN o.order_id END) > 10  THEN 'Rui ro cao'
        WHEN COUNT(DISTINCT CASE WHEN o.discount_amount * 1.0 / NULLIF(o.gross_revenue, 0) > 0.3
                                 THEN o.order_id END) > 5   THEN 'Can xem xet'
        ELSE 'Binh thuong'
    END                                                                 AS "Danh gia"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_staff s ON o.seller_staff_key = s.staff_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND o.seller_staff_key IS NOT NULL
GROUP BY o.seller_staff_key, s.full_name
ORDER BY SUM(o.discount_amount) DESC
LIMIT 30
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["Danh gia"],
        "type": "single",
        "operator": "=",
        "value": "Rui ro cao",
        "color": "#EF8C8C",
        "highlight_row": true
      },
      {
        "columns": ["Danh gia"],
        "type": "single",
        "operator": "=",
        "value": "Can xem xet",
        "color": "#F9D45C",
        "highlight_row": false
      }
    ],
    "column_settings": {
      "Tong CK da cap": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "CK trung binh %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Tập trung nhân viên × khách hàng — dấu hiệu cấu kết

## Tập trung nhân viên × khách hàng — dấu hiệu cấu kết

> **Signal:** 1 nhân viên push cùng khách hàng >= 3 lần trong 30 ngày với avg discount > 20% → cần điều tra. **Action:** Điều tra trong vòng 1 tuần.

```json metabase-pos
{ "row": 33, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Staff × Customer Concentration (Potential Collusion)

Bang 1 nhan vien push nhieu don cho cung 1 KH voi chiet khau cao. **Scope: Retail, last 30 days. HAVING: order_count >= 3 AND avg_discount > 20%.**

```sql
SELECT
    COALESCE(s.full_name, o.seller_staff_key)                                   AS "Nhan vien",
    c.phone                                                                      AS "So DT KH",
    c.full_name                                                                  AS "Ten KH",
    COUNT(DISTINCT o.order_id)                                                   AS "So don 30d",
    SUM(o.discount_amount)                                                       AS "Tong CK",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1)  AS "CK trung binh %"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_staff s ON o.seller_staff_key = s.staff_key
WHERE o.scope_retail
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  AND o.seller_staff_key IS NOT NULL
GROUP BY o.seller_staff_key, s.full_name, c.customer_key, c.phone, c.full_name
HAVING COUNT(DISTINCT o.order_id) >= 3
   AND ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) > 20
ORDER BY SUM(o.discount_amount) DESC
LIMIT 50
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.column_formatting": [
      {
        "columns": ["So don 30d"],
        "type": "single",
        "operator": ">=",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ],
    "column_settings": {
      "Tong CK": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "CK trung binh %": { "suffix": "%" }
    }
  }
}
```

```json metabase-pos
{ "row": 34, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers + dim_promotions + dim_staff · **Cadence:** rolling-30d · **Scope:** scope_retail (pre-computed) · **Review cadence:** Hàng tuần với Finance + Sales Ops

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

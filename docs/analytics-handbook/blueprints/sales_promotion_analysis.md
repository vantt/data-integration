# 📘 Blueprint: Sales Promotion & Discount Analysis

**Design Spec**: [Sales Promotion & Discount Analysis](../designs/sales_promotion_analysis.md)

> **Target Collection:** `Marketing & Customers`
> **Role:** Marketing Manager, Sales Ops, Finance
> **Archetype:** Exploratory Tool (3 tabs)

Ad-hoc analysis — evaluate campaign ROI, discount spending, promo effectiveness. 3 tabs: Tong quan chiet khau (Discount Overview), Hieu suat khuyen mai (Promotion Performance), Phan tich kenh & chi tiet (Channel Impact & Detail). MoM = last 30 days vs previous 30 days.

## 📂 Collection: Marketing & Customers

Channel performance, customer acquisition, retention, segmentation, and campaign analysis.

<!-- Filters removed: date/all-options and string/= types don't work with native SQL template tags in DuckDB.
     Date scoping is hardcoded in each SQL (last 30 days). -->

---

### 🖥️ Dashboard: Promotion & Discount Analysis

**Description**: Phan tich khuyen mai & chiet khau — 3 tabs: Tong quan chiet khau, Hieu suat khuyen mai, Phan tich kenh & chi tiet. MoM comparison (30 days vs previous 30 days). Loai bo don CANCELLED.

---

### 📑 Tab: Tong quan chiet khau

#### 📝 Text: Kiểm soát chi phí chiết khấu — có vượt ngưỡng và đang tăng hay giảm?

## Kiểm soát chi phí chiết khấu — có vượt ngưỡng và đang tăng hay giảm?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total Discount Amount

Tong tien chiet khau ky nay voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
),
prev_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '60 days'
      AND order_timestamp < current_date - INTERVAL '30 days'
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
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Ky truoc",
        "label": "vs 30 ngày trước"
      }
    ],
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
{ "row": 1, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Discount Rate %

Ty le chiet khau / GMV voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT
        CASE WHEN SUM(gross_revenue) = 0 THEN 0
             ELSE ROUND(SUM(discount_amount) * 100.0 / SUM(gross_revenue), 1) END as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
),
prev_period AS (
    SELECT
        CASE WHEN SUM(gross_revenue) = 0 THEN 0
             ELSE ROUND(SUM(discount_amount) * 100.0 / SUM(gross_revenue), 1) END as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '60 days'
      AND order_timestamp < current_date - INTERVAL '30 days'
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
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Ky truoc",
        "label": "vs 30 ngày trước"
      }
    ],
    "column_settings": {
      "Ty le CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Discount Frequency %

Phan tram don hang co chiet khau voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
                        / COUNT(DISTINCT order_id), 1) END as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT order_id) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) * 100.0
                        / COUNT(DISTINCT order_id), 1) END as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '60 days'
      AND order_timestamp < current_date - INTERVAL '30 days'
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
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Ky truoc",
        "label": "vs 30 ngày trước"
      }
    ],
    "column_settings": {
      "Tan suat CK %": {
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Discounted Orders

So don hang co chiet khau voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
),
prev_period AS (
    SELECT COUNT(DISTINCT CASE WHEN discount_amount > 0 THEN order_id END) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '60 days'
      AND order_timestamp < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "Don co CK",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Ky truoc",
        "label": "vs 30 ngày trước"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 4 }
```

#### 📝 Text: So sánh Promo vs Non-Promo — khuyến mãi có uplift AOV?

## So sánh Promo vs Non-Promo — khuyến mãi có uplift AOV?

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Promo vs Non-Promo Summary

So sanh Revenue, Orders, AOV giua Promo va Non-Promo — grouped bar.

```sql
WITH base AS (
    SELECT
        CASE WHEN discount_amount > 0 THEN 'Promo' ELSE 'Non-Promo' END as segment,
        net_revenue,
        order_id
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
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
{ "row": 6, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: AOV Uplift

AOV(Promo) vs AOV(Non-Promo) delta — single value.

```sql
WITH base AS (
    SELECT
        CASE WHEN discount_amount > 0 THEN 'Promo' ELSE 'Non-Promo' END as segment,
        net_revenue,
        order_id
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
),
aov AS (
    SELECT
        CASE WHEN COUNT(DISTINCT CASE WHEN segment = 'Promo' THEN order_id END) = 0 THEN 0
             ELSE SUM(CASE WHEN segment = 'Promo' THEN net_revenue ELSE 0 END)
                  / COUNT(DISTINCT CASE WHEN segment = 'Promo' THEN order_id END) END as promo_aov,
        CASE WHEN COUNT(DISTINCT CASE WHEN segment = 'Non-Promo' THEN order_id END) = 0 THEN 0
             ELSE SUM(CASE WHEN segment = 'Non-Promo' THEN net_revenue ELSE 0 END)
                  / COUNT(DISTINCT CASE WHEN segment = 'Non-Promo' THEN order_id END) END as non_promo_aov
    FROM base
)
SELECT
    promo_aov as "AOV Promo",
    non_promo_aov as "AOV Non-Promo"
FROM aov
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "benchmark",
        "type": "anotherColumn",
        "column": "AOV Non-Promo",
        "label": "vs Non-Promo AOV"
      }
    ],
    "column_settings": {
      "AOV Promo": {
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
{ "row": 6, "col": 12, "size_x": 6, "size_y": 6 }
```

#### 📝 Text: Phân tích độ sâu chiết khấu — phát hiện đơn bất thường > 30%

## Phân tích độ sâu chiết khấu — phát hiện đơn bất thường > 30%

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Depth Histogram

Phan bo don hang theo % chiet khau (0-10%, 10-20%, 20-30%, 30%+).

```sql
SELECT
    CASE
        WHEN gross_revenue = 0 THEN 'N/A'
        WHEN discount_amount / gross_revenue < 0.1 THEN '0-10%'
        WHEN discount_amount / gross_revenue < 0.2 THEN '10-20%'
        WHEN discount_amount / gross_revenue < 0.3 THEN '20-30%'
        ELSE '30%+'
    END as "Muc chiet khau",
    COUNT(DISTINCT order_id) as "So don"
FROM fact_orders
WHERE status != 'CANCELLED'
  AND order_timestamp >= current_date - INTERVAL '30 days'
  AND order_timestamp < current_date
  AND discount_amount > 0
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
{ "row": 13, "col": 0, "size_x": 12, "size_y": 6 }
```

#### ❓ Question: Avg Discount % by Channel

Ranking kenh theo ty le chiet khau trung binh — horizontal bar.

```sql
SELECT
    c.channel_name as "Kenh",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as "Ty le CK %"
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
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
{ "row": 13, "col": 12, "size_x": 6, "size_y": 6 }
```

#### 📝 Text: Theo dõi xu hướng chiết khấu — trend amount và rate

## Theo dõi xu hướng chiết khấu — trend amount và rate

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Discount Amount & Rate Trend

Xu huong tien chiet khau (bar) va ty le CK (line) theo thang — combo chart.

```sql
SELECT
    date_trunc('month', order_timestamp)::date as "Thang",
    SUM(discount_amount) as "Tien CK",
    ROUND(SUM(discount_amount) * 100.0 / NULLIF(SUM(gross_revenue), 0), 1) as "Ty le CK %"
FROM fact_orders
WHERE status != 'CANCELLED'
  AND order_timestamp >= current_date - INTERVAL '6 months'
  AND order_timestamp < current_date
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
{ "row": 20, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Hieu suat khuyen mai

#### 📝 Text: Xác định promotion hiệu quả — ranking doanh thu và usage

## Xác định promotion hiệu quả — ranking doanh thu và usage

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Total Promo Revenue

Tong doanh thu tu don co promo voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND discount_amount > 0
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
),
prev_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND discount_amount > 0
      AND order_timestamp >= current_date - INTERVAL '60 days'
      AND order_timestamp < current_date - INTERVAL '30 days'
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
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Ky truoc",
        "label": "vs 30 ngày trước"
      }
    ],
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
{ "row": 1, "col": 0, "size_x": 6, "size_y": 4 }
```

#### ❓ Question: Promo Usage Count

Tong so don dung promo voi MoM comparison.

```sql
WITH
this_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND discount_amount > 0
      AND order_timestamp >= current_date - INTERVAL '30 days'
      AND order_timestamp < current_date
),
prev_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE status != 'CANCELLED'
      AND discount_amount > 0
      AND order_timestamp >= current_date - INTERVAL '60 days'
      AND order_timestamp < current_date - INTERVAL '30 days'
)
SELECT
    tp.val as "Luot dung",
    pp.val as "Ky truoc"
FROM this_period tp, prev_period pp
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Ky truoc",
        "label": "vs 30 ngày trước"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 4 }
```

#### ❓ Question: Unique Promos Active

So chuong trinh khuyen mai dang active — single value (khong co MoM).

```sql
SELECT COUNT(DISTINCT p.promotion_code) as "So CT active"
FROM fact_orders o
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.status != 'CANCELLED'
  AND o.discount_amount > 0
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
  AND p.promotion_code IS NOT NULL
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 4 }
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
    LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.status != 'CANCELLED'
      AND o.discount_amount > 0
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      AND p.promotion_code IS NOT NULL
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT p.promotion_code) = 0 THEN 0
             ELSE SUM(o.net_revenue) / COUNT(DISTINCT p.promotion_code) END as val
    FROM fact_orders o
    LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.status != 'CANCELLED'
      AND o.discount_amount > 0
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
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
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Ky truoc",
        "label": "vs 30 ngày trước"
      }
    ],
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
{ "row": 1, "col": 14, "size_x": 4, "size_y": 4 }
```

#### 📝 Text: Review top 10 promotion — doanh thu và lượt sử dụng

## Review top 10 promotion — doanh thu và lượt sử dụng

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Top 10 Promotions by Revenue

Ranking chuong trinh khuyen mai theo doanh thu — horizontal bar.

```sql
SELECT
    COALESCE(p.promotion_code, 'Khong ro') as "Ma KM",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.status != 'CANCELLED'
  AND o.discount_amount > 0
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
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
{ "row": 6, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Top 10 Promotions by Usage

Ranking chuong trinh khuyen mai theo luot su dung — horizontal bar.

```sql
SELECT
    COALESCE(p.promotion_code, 'Khong ro') as "Ma KM",
    COUNT(DISTINCT o.order_id) as "Luot dung"
FROM fact_orders o
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.status != 'CANCELLED'
  AND o.discount_amount > 0
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
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
{ "row": 6, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: Tra cứu chi tiết promotion — code, usage, revenue, discount rate

## Tra cứu chi tiết promotion — code, usage, revenue, discount rate

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
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
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.status != 'CANCELLED'
  AND o.discount_amount > 0
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
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
{ "row": 13, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Theo dõi xu hướng sử dụng promotion — top 5 codes

## Theo dõi xu hướng sử dụng promotion — top 5 codes

```json metabase-pos
{ "row": 22, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Promo Usage Trend

Phan bo luot dung promo theo thang, chia theo top 5 codes — stacked bar.

```sql
WITH top5 AS (
    SELECT p.promotion_code
    FROM fact_orders o
    LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
    WHERE o.status != 'CANCELLED'
      AND o.discount_amount > 0
      AND o.order_timestamp >= current_date - INTERVAL '6 months'
      AND o.order_timestamp < current_date
      AND p.promotion_code IS NOT NULL
    GROUP BY 1
    ORDER BY COUNT(DISTINCT o.order_id) DESC
    LIMIT 5
)
SELECT
    date_trunc('month', o.order_timestamp)::date as "Thang",
    COALESCE(p.promotion_code, 'Khac') as "Ma KM",
    COUNT(DISTINCT o.order_id) as "So don"
FROM fact_orders o
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
WHERE o.status != 'CANCELLED'
  AND o.discount_amount > 0
  AND o.order_timestamp >= current_date - INTERVAL '6 months'
  AND o.order_timestamp < current_date
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
{ "row": 23, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Phan tich kenh & chi tiet

#### 📝 Text: Phân tích tác động promo theo kênh — kênh nào phụ thuộc nhiều?

## Phân tích tác động promo theo kênh — kênh nào phụ thuộc nhiều?

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Promo Revenue Share by Channel

Ty le doanh thu promo vs non-promo theo kenh — stacked bar.

```sql
SELECT
    c.channel_name as "Kenh",
    SUM(CASE WHEN o.discount_amount > 0 THEN o.net_revenue ELSE 0 END) as "DT Promo",
    SUM(CASE WHEN o.discount_amount = 0 THEN o.net_revenue ELSE 0 END) as "DT Non-Promo"
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
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
{ "row": 1, "col": 0, "size_x": 9, "size_y": 6 }
```

#### ❓ Question: Discount Rate by Channel

Ranking kenh theo ty le chiet khau — horizontal bar.

```sql
SELECT
    c.channel_name as "Kenh",
    ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as "Ty le CK %"
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
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
{ "row": 1, "col": 9, "size_x": 9, "size_y": 6 }
```

#### 📝 Text: So sánh hiệu suất kênh MoM — highlight biến động lớn

## So sánh hiệu suất kênh MoM — highlight biến động lớn

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Channel Promo Performance Table

Bang chi tiet hieu suat khuyen mai theo kenh — conditional formatting tren MoM Change %.

```sql
WITH
this_period AS (
    SELECT
        c.channel_name as channel,
        COUNT(DISTINCT CASE WHEN o.discount_amount > 0 THEN o.order_id END) as promo_orders,
        SUM(CASE WHEN o.discount_amount > 0 THEN o.net_revenue ELSE 0 END) as promo_revenue,
        SUM(o.discount_amount) as discount_amount,
        ROUND(SUM(o.discount_amount) * 100.0 / NULLIF(SUM(o.gross_revenue), 0), 1) as discount_rate
    FROM fact_orders o
    LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
    GROUP BY 1
),
prev_period AS (
    SELECT
        c.channel_name as channel,
        SUM(CASE WHEN o.discount_amount > 0 THEN o.net_revenue ELSE 0 END) as promo_revenue
    FROM fact_orders o
    LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Điều tra đơn chiết khấu cao — flag đơn > 30% CK để audit

## Điều tra đơn chiết khấu cao — flag đơn > 30% CK để audit

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: High-Discount Orders List

Danh sach don hang co chiet khau > 30% — conditional formatting tren Discount %.

```sql
SELECT
    o.order_code as "Ma don",
    o.order_timestamp::date as "Ngay",
    c.channel_name as "Kenh",
    COALESCE(p.promotion_code, o.discount_codes, '') as "Ma KM",
    o.gross_revenue as "Doanh thu goc",
    o.discount_amount as "Tien CK",
    ROUND(o.discount_amount * 100.0 / NULLIF(o.gross_revenue, 0), 1) as "Ty le CK %",
    o.net_revenue as "Doanh thu thuan"
FROM fact_orders o
LEFT JOIN dim_promotions p ON o.promotion_key = p.promotion_key
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 9 }
```

#### 📝 Text: Footer

Source: fact_orders · dim_promotions · dim_channels · Updated daily · Excludes cancelled orders

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```

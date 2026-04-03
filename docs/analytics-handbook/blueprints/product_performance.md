# Product Performance Blueprint

**Design Spec**: [Product Performance](../designs/product_performance.md)

Dashboard theo doi hieu suat san pham — doanh thu, so luong, xu huong, phan tich loai SP, top/bottom products. MoM comparison (last 30 days vs previous 30 days).

## 📂 Collection: Operations > Periodic Reviews

### Dashboard: Product Performance

**Description**: Phan tich hieu suat san pham — doanh thu, so luong ban, xu huong MoM, phan bo theo loai SP, top/bottom products across 3 tabs.

---

#### Filter: Date Range

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past30days"
}
```

#### Filter: Loai san pham

```json metabase-filter
{
  "slug": "product_type",
  "type": "string/="
}
```

#### Filter: Kenh ban hang

```json metabase-filter
{
  "slug": "channel",
  "type": "string/="
}
```

---

### 📑 Tab: Tong quan

#### 📝 Text: Overview Heading

# Review hieu suat san pham thang — doanh thu, velocity, va xu huong MoM

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Doanh thu san pham

Hero metric — tong doanh thu san pham last 30 days vs previous 30 days.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
)
SELECT
    t.val as "Doanh thu san pham",
    p.val as "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "Doanh thu san pham": {
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

#### Question: So luong ban

Supporting KPI — tong quantity sold last 30 days vs previous 30 days.

```sql
WITH
this_period AS (
    SELECT COALESCE(SUM(s.quantity), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(s.quantity), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
)
SELECT
    t.val as "So luong ban",
    p.val as "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 4 }
```

#### Question: So san pham ban duoc

Supporting KPI — distinct products co sales last 30 days vs previous 30 days.

```sql
WITH
this_period AS (
    SELECT COUNT(DISTINCT s.product_key) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT COUNT(DISTINCT s.product_key) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
)
SELECT
    t.val as "So san pham ban duoc",
    p.val as "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 10, "size_x": 4, "size_y": 4 }
```

#### Question: Doanh thu trung binh/san pham

Supporting KPI — revenue per distinct product last 30 days vs previous 30 days.

```sql
WITH
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT s.product_key) = 0 THEN 0
             ELSE ROUND(SUM(s.revenue) / COUNT(DISTINCT s.product_key), 0)
        END as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT s.product_key) = 0 THEN 0
             ELSE ROUND(SUM(s.revenue) / COUNT(DISTINCT s.product_key), 0)
        END as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
)
SELECT
    t.val as "DT trung binh/SP",
    p.val as "Thang truoc"
FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "mom",
        "type": "anotherColumn",
        "column": "Thang truoc",
        "label": "vs thang truoc"
      }
    ],
    "column_settings": {
      "DT trung binh/SP": {
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

---

#### 📝 Text: Trend Heading

# Phan tich xu huong doanh thu san pham — momentum MoM

```json metabase-pos
{ "row": 5, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Doanh thu san pham theo ngay

Trend doanh thu hang ngay — overlay this month vs last month.

```sql
WITH
this_month AS (
    SELECT
        date(o.order_timestamp) as ngay,
        COALESCE(SUM(s.revenue), 0) as doanh_thu
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY date(o.order_timestamp)
),
last_month AS (
    SELECT
        date(o.order_timestamp) + INTERVAL '30 days' as ngay,
        COALESCE(SUM(s.revenue), 0) as doanh_thu
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY date(o.order_timestamp) + INTERVAL '30 days'
)
SELECT
    COALESCE(t.ngay, l.ngay) as "Ngay",
    COALESCE(t.doanh_thu, 0) as "Thang nay",
    COALESCE(l.doanh_thu, 0) as "Thang truoc"
FROM this_month t
FULL OUTER JOIN last_month l ON t.ngay = l.ngay
ORDER BY "Ngay"
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Thang nay", "Thang truoc"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Doanh thu (VND)",
    "series_settings": {
      "Thang nay": { "color": "#509EE3" },
      "Thang truoc": { "color": "#C2D2E9" }
    },
    "column_settings": {
      "Thang nay": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Thang truoc": {
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

#### Question: So luong ban theo ngay

Trend quantity hang ngay — overlay this month vs last month.

```sql
WITH
this_month AS (
    SELECT
        date(o.order_timestamp) as ngay,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY date(o.order_timestamp)
),
last_month AS (
    SELECT
        date(o.order_timestamp) + INTERVAL '30 days' as ngay,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY date(o.order_timestamp) + INTERVAL '30 days'
)
SELECT
    COALESCE(t.ngay, l.ngay) as "Ngay",
    COALESCE(t.so_luong, 0) as "Thang nay",
    COALESCE(l.so_luong, 0) as "Thang truoc"
FROM this_month t
FULL OUTER JOIN last_month l ON t.ngay = l.ngay
ORDER BY "Ngay"
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Thang nay", "Thang truoc"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "So luong",
    "series_settings": {
      "Thang nay": { "color": "#88BDE6" },
      "Thang truoc": { "color": "#C2D2E9" }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Contribution Heading

# Xac dinh dong gop theo loai san pham — ranking va composition

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Doanh thu theo loai san pham

Ranking loai SP theo doanh thu — horizontal bar.

```sql
SELECT
    pt.product_type_name as "Loai san pham",
    COALESCE(SUM(s.revenue), 0) as "Doanh thu"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
  [[AND pt.product_type_name = {{product_type}}]]
  [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
GROUP BY pt.product_type_name
ORDER BY "Doanh thu" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loai san pham"],
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
{ "row": 13, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Ty trong doanh thu theo loai san pham

Phan bo % doanh thu theo loai SP — donut chart.

```sql
SELECT
    pt.product_type_name as "Loai san pham",
    COALESCE(SUM(s.revenue), 0) as "Doanh thu"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
  [[AND pt.product_type_name = {{product_type}}]]
  [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
GROUP BY pt.product_type_name
ORDER BY "Doanh thu" DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.percent_visibility": "legend"
  }
}
```

```json metabase-pos
{ "row": 13, "col": 9, "size_x": 9, "size_y": 6 }
```

---

### 📑 Tab: Phan tich loai san pham

#### 📝 Text: Category Growth Heading

# Danh gia tang truong theo loai san pham — dieu chinh product mix

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Tang truong doanh thu theo loai SP

MoM % change by category — horizontal bar with conditional colors.

```sql
WITH
this_period AS (
    SELECT
        pt.product_type_name as loai,
        COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND pt.product_type_name = {{product_type}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY pt.product_type_name
),
prev_period AS (
    SELECT
        pt.product_type_name as loai,
        COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND pt.product_type_name = {{product_type}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY pt.product_type_name
)
SELECT
    COALESCE(t.loai, p.loai) as "Loai san pham",
    CASE
        WHEN COALESCE(p.val, 0) = 0 THEN NULL
        ELSE ROUND((COALESCE(t.val, 0) - p.val) * 100.0 / p.val, 1)
    END as "Tang truong MoM %"
FROM this_period t
FULL OUTER JOIN prev_period p ON t.loai = p.loai
ORDER BY "Tang truong MoM %" DESC NULLS LAST
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Loai san pham"],
    "graph.metrics": ["Tang truong MoM %"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Tang truong MoM %",
    "column_settings": {
      "Tang truong MoM %": {
        "number_style": "percent",
        "scale": 0.01,
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 1, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Category Mix Heading

# Theo doi category mix shift — loai nao dang chiem uu the?

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Category Mix Trend

Cau thanh doanh thu theo loai SP qua thoi gian — stacked area.

```sql
SELECT
    date(o.order_timestamp) as "Ngay",
    pt.product_type_name as "Loai san pham",
    COALESCE(SUM(s.revenue), 0) as "Doanh thu"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
  [[AND pt.product_type_name = {{product_type}}]]
  [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
GROUP BY date(o.order_timestamp), pt.product_type_name
ORDER BY "Ngay"
```

```json metabase-viz
{
  "display": "area",
  "visualization_settings": {
    "stackable.stack_type": "stacked",
    "graph.dimensions": ["Ngay", "Loai san pham"],
    "graph.metrics": ["Doanh thu"],
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Category Detail Heading

# Review chi tiet loai san pham — highlight tang/giam manh

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Bang hieu suat loai san pham

Loai SP, Doanh thu, So luong, Revenue/unit, MoM % — conditional formatting on MoM columns.

```sql
WITH
this_period AS (
    SELECT
        pt.product_type_name as loai,
        COALESCE(SUM(s.revenue), 0) as doanh_thu,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND pt.product_type_name = {{product_type}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY pt.product_type_name
),
prev_period AS (
    SELECT
        pt.product_type_name as loai,
        COALESCE(SUM(s.revenue), 0) as doanh_thu,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND pt.product_type_name = {{product_type}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY pt.product_type_name
)
SELECT
    COALESCE(t.loai, p.loai) as "Loai san pham",
    COALESCE(t.doanh_thu, 0) as "Doanh thu",
    COALESCE(t.so_luong, 0) as "So luong",
    CASE WHEN COALESCE(t.so_luong, 0) = 0 THEN 0
         ELSE ROUND(COALESCE(t.doanh_thu, 0) / t.so_luong, 0)
    END as "DT/don vi",
    CASE WHEN COALESCE(p.doanh_thu, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(t.doanh_thu, 0) - p.doanh_thu) * 100.0 / p.doanh_thu, 1)
    END as "DT MoM %",
    CASE WHEN COALESCE(p.so_luong, 0) = 0 THEN NULL
         ELSE ROUND((COALESCE(t.so_luong, 0) - p.so_luong) * 100.0 / p.so_luong, 1)
    END as "SL MoM %"
FROM this_period t
FULL OUTER JOIN prev_period p ON t.loai = p.loai
ORDER BY COALESCE(t.doanh_thu, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "DT/don vi": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "table.column_formatting": [
      {
        "columns": ["DT MoM %", "SL MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["DT MoM %", "SL MoM %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 9 }
```

---

### 📑 Tab: San pham ban chay & ban cham

#### 📝 Text: Top Products Heading

# Xac dinh top 20 san pham ban chay — focus marketing va stock

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top 20 SP theo doanh thu

Ranking san pham theo revenue — horizontal bar.

```sql
SELECT
    p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END as "San pham",
    COALESCE(SUM(s.revenue), 0) as "Doanh thu"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_products p ON s.product_key = p.product_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
  [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
  [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
GROUP BY p.product_name, p.variant_name
ORDER BY "Doanh thu" DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
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
{ "row": 1, "col": 0, "size_x": 9, "size_y": 9 }
```

#### Question: Top 20 SP theo so luong

Ranking san pham theo quantity — horizontal bar.

```sql
SELECT
    p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END as "San pham",
    COALESCE(SUM(s.quantity), 0) as "So luong"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_products p ON s.product_key = p.product_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
  [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
  [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
GROUP BY p.product_name, p.variant_name
ORDER BY "So luong" DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["So luong"],
    "graph.colors": ["#88BDE6"],
    "graph.x_axis.title_text": "So luong"
  }
}
```

```json metabase-pos
{ "row": 1, "col": 9, "size_x": 9, "size_y": 9 }
```

---

#### 📝 Text: Growth Decline Heading

# Canh bao som — san pham tang truong va sut giam manh nhat

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top 10 SP tang truong MoM

San pham co % tang truong cao nhat — horizontal bar.

```sql
WITH
this_period AS (
    SELECT
        s.product_key,
        p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END as ten_sp,
        COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_products p ON s.product_key = p.product_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY s.product_key, p.product_name, p.variant_name
),
prev_period AS (
    SELECT
        s.product_key,
        COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY s.product_key
)
SELECT
    t.ten_sp as "San pham",
    ROUND((t.val - p.val) * 100.0 / p.val, 1) as "Tang truong %"
FROM this_period t
JOIN prev_period p ON t.product_key = p.product_key
WHERE p.val > 0 AND t.val > p.val
ORDER BY "Tang truong %" DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["Tang truong %"],
    "graph.colors": ["#84BB4C"],
    "graph.x_axis.title_text": "Tang truong MoM %"
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Top 10 SP sut giam MoM

San pham co % sut giam lon nhat — horizontal bar.

```sql
WITH
this_period AS (
    SELECT
        s.product_key,
        p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END as ten_sp,
        COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_products p ON s.product_key = p.product_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY s.product_key, p.product_name, p.variant_name
),
prev_period AS (
    SELECT
        s.product_key,
        COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY s.product_key
)
SELECT
    t.ten_sp as "San pham",
    ROUND((t.val - p.val) * 100.0 / p.val, 1) as "Sut giam %"
FROM this_period t
JOIN prev_period p ON t.product_key = p.product_key
WHERE p.val > 0 AND t.val < p.val
ORDER BY "Sut giam %" ASC
LIMIT 10
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["Sut giam %"],
    "graph.colors": ["#EF8C8C"],
    "graph.x_axis.title_text": "Sut giam MoM %"
  }
}
```

```json metabase-pos
{ "row": 11, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Velocity Heading

# Phan tich velocity — san pham nao quay nhanh nhat?

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top 20 SP theo daily velocity

Units/day — san pham quay nhanh nhat.

```sql
SELECT
    p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END as "San pham",
    ROUND(SUM(s.quantity) * 1.0 / 30, 2) as "Units/ngay"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_products p ON s.product_key = p.product_key
WHERE o.status != 'CANCELLED'
  AND o.order_timestamp >= current_date - INTERVAL '30 days'
  AND o.order_timestamp < current_date
  [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
  [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
GROUP BY p.product_name, p.variant_name
HAVING SUM(s.quantity) > 0
ORDER BY "Units/ngay" DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["Units/ngay"],
    "graph.colors": ["#7172AD"],
    "graph.x_axis.title_text": "Units/ngay"
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Detail Table Heading

# Tra cuu chi tiet san pham — tim kiem, sap xep, loc tu do

```json metabase-pos
{ "row": 24, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Bang chi tiet san pham

Ten SP, Loai, Doanh thu, So luong, Velocity, MoM % — conditional formatting on MoM columns.

```sql
WITH
this_period AS (
    SELECT
        s.product_key,
        p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END as ten_sp,
        pt.product_type_name as loai,
        COALESCE(SUM(s.revenue), 0) as doanh_thu,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_products p ON s.product_key = p.product_key
    LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '30 days'
      AND o.order_timestamp < current_date
      [[AND pt.product_type_name = {{product_type}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY s.product_key, p.product_name, p.variant_name, pt.product_type_name
),
prev_period AS (
    SELECT
        s.product_key,
        COALESCE(SUM(s.revenue), 0) as doanh_thu,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp >= current_date - INTERVAL '60 days'
      AND o.order_timestamp < current_date - INTERVAL '30 days'
      [[AND pt.product_type_name = {{product_type}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
    GROUP BY s.product_key
)
SELECT
    t.ten_sp as "San pham",
    t.loai as "Loai",
    t.doanh_thu as "Doanh thu",
    t.so_luong as "So luong",
    ROUND(t.so_luong * 1.0 / 30, 2) as "Units/ngay",
    CASE WHEN COALESCE(p.doanh_thu, 0) = 0 THEN NULL
         ELSE ROUND((t.doanh_thu - p.doanh_thu) * 100.0 / p.doanh_thu, 1)
    END as "DT MoM %",
    CASE WHEN COALESCE(p.so_luong, 0) = 0 THEN NULL
         ELSE ROUND((t.so_luong - p.so_luong) * 100.0 / p.so_luong, 1)
    END as "SL MoM %"
FROM this_period t
LEFT JOIN prev_period p ON t.product_key = p.product_key
ORDER BY t.doanh_thu DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "table.column_formatting": [
      {
        "columns": ["DT MoM %", "SL MoM %"],
        "type": "single",
        "operator": ">=",
        "value": 0,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["DT MoM %", "SL MoM %"],
        "type": "single",
        "operator": "<",
        "value": 0,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 9 }
```

---

#### 📝 Text: Footer

Source: fact_orders · dim_products · Updated daily · Excludes cancelled orders

```json metabase-pos
{ "row": 34, "col": 0, "size_x": 18, "size_y": 1 }
```

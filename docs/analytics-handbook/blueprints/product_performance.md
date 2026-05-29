# Product Performance [Cross] Blueprint

**Design Spec**: [Product Performance](../designs/product_performance.md)

Dashboard theo doi hieu suat san pham — doanh thu, so luong, xu huong, phan tich loai SP, top/bottom products. MoM comparison (last 30 days vs previous 30 days).

## 📂 Collection: Analytics

### Dashboard: Product Performance [Cross]

**Description**: Audience: Analyst / Product Manager. Scope: Cross-segment product analysis. Phan tich hieu suat san pham — doanh thu, so luong ban, xu huong MoM, phan bo theo loai SP, top/bottom products across 3 tabs.

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
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Doanh thu san pham

Hero metric — tong doanh thu san pham this period vs previous period.

```sql
WITH
filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
this_period AS (
    SELECT COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(s.revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.order_timestamp::DATE <  filter_bounds.p_start
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
{ "row": 4, "col": 0, "size_x": 6, "size_y": 4 }
```

#### Question: So luong ban

Supporting KPI — tong quantity sold this period vs previous period.

```sql
WITH
filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
this_period AS (
    SELECT COALESCE(SUM(s.quantity), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(s.quantity), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.order_timestamp::DATE <  filter_bounds.p_start
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
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 4, "size_y": 4 }
```

#### Question: So san pham ban duoc

Supporting KPI — distinct products co sales this period vs previous period.

```sql
WITH
filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
this_period AS (
    SELECT COUNT(DISTINCT s.product_key) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT COUNT(DISTINCT s.product_key) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.order_timestamp::DATE <  filter_bounds.p_start
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
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 4, "col": 10, "size_x": 4, "size_y": 4 }
```

#### Question: Doanh thu trung binh/san pham

Supporting KPI — revenue per distinct product this period vs previous period.

```sql
WITH
filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT s.product_key) = 0 THEN 0
             ELSE ROUND(SUM(s.revenue) / COUNT(DISTINCT s.product_key), 0)
        END as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT s.product_key) = 0 THEN 0
             ELSE ROUND(SUM(s.revenue) / COUNT(DISTINCT s.product_key), 0)
        END as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.order_timestamp::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.order_timestamp::DATE <  filter_bounds.p_start
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
{ "row": 4, "col": 14, "size_x": 4, "size_y": 4 }
```

---

#### 📝 Text: Trend Heading

# Phan tich xu huong doanh thu san pham — momentum MoM

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
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
{ "row": 10, "col": 0, "size_x": 12, "size_y": 6 }
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
{ "row": 10, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Contribution Heading

# Xac dinh dong gop theo loai san pham — ranking va composition

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 17, "col": 0, "size_x": 9, "size_y": 6 }
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
{ "row": 17, "col": 9, "size_x": 9, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** int_misa_sales_lines + fact_sales · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Phan tich loai san pham


#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
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

#### 📝 Text: Category Growth Heading

# Danh gia tang truong theo loai san pham — dieu chinh product mix

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 3, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Category Mix Heading

# Theo doi category mix shift — loai nao dang chiem uu the?

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 10, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Category Detail Heading

# Review chi tiet loai san pham — highlight tang/giam manh

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 17, "col": 0, "size_x": 18, "size_y": 9 }
```

---


#### 📝 Text: Source & Freshness

**Source:** int_misa_sales_lines + fact_sales · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: San pham ban chay & ban cham


#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(o.order_timestamp)::DATE AS p_start, MAX(o.order_timestamp)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      [[AND {{date_range}}]]
      [[AND s.channel_key IN (SELECT channel_key FROM dim_channels WHERE channel_name = {{channel}})]]
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

#### 📝 Text: Top Products Heading

# Xac dinh top 20 san pham ban chay — focus marketing va stock

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 3, "col": 0, "size_x": 9, "size_y": 9 }
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
{ "row": 3, "col": 9, "size_x": 9, "size_y": 9 }
```

---

#### 📝 Text: Growth Decline Heading

# Canh bao som — san pham tang truong va sut giam manh nhat

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 13, "col": 0, "size_x": 9, "size_y": 6 }
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
{ "row": 13, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Velocity Heading

# Phan tich velocity — san pham nao quay nhanh nhat?

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 20, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Detail Table Heading

# Tra cuu chi tiet san pham — tim kiem, sap xep, loc tu do

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 27, "col": 0, "size_x": 18, "size_y": 9 }
```



#### 📝 Text: Source & Freshness

**Source:** int_misa_sales_lines + fact_sales · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Loi nhuan


#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
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

#### 📝 Text: Profitability Heading

# Bien loi nhuan gop theo san pham — dua tren gia von tu MISA

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Gross Margin %

Ty le bien loi nhuan gop tong the — gauge theo nguong hieu suat.

```sql
SELECT
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Bien loi nhuan gop %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND posting_date >= {{date_range}}]]
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0,  "max": 25,  "color": "#EF8C8C", "label": "Thap" },
      { "min": 25, "max": 40,  "color": "#F9D45C", "label": "Trung binh" },
      { "min": 40, "max": 100, "color": "#84BB4C", "label": "Tot" }
    ]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 5 }
```

#### Question: Top 20 san pham theo loi nhuan

Top 20 san pham co loi nhuan gop cao nhat — horizontal bar.

```sql
SELECT
    product_name AS "San pham",
    SUM(gross_profit) AS "Loi nhuan gop"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND posting_date >= {{date_range}}]]
GROUP BY product_name
ORDER BY "Loi nhuan gop" DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["San pham"],
    "graph.metrics": ["Loi nhuan gop"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Loi nhuan gop (VND)",
    "column_settings": {
      "Loi nhuan gop": {
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
{ "row": 3, "col": 6, "size_x": 12, "size_y": 8 }
```

---

#### 📝 Text: Channel Margin Heading

# So sanh margin giua cac kenh ban hang

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Margin by Channel

Loi nhuan gop va bien LN theo kenh ban hang — horizontal bar.

```sql
SELECT
    channel_name AS "Kenh ban hang",
    SUM(revenue_net_of_discount) AS "Doanh thu",
    SUM(cogs) AS "Gia von",
    SUM(gross_profit) AS "Loi nhuan gop",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND posting_date >= {{date_range}}]]
GROUP BY channel_name
ORDER BY "Margin %" DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh ban hang"],
    "graph.metrics": ["Margin %"],
    "graph.x_axis.title_text": "Bien loi nhuan gop (%)",
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
      },
      "Loi nhuan gop": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Margin %": {
        "number_style": "decimal",
        "decimals": 1,
        "suffix": "%"
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Margin %"],
        "type": "single",
        "operator": ">",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      },
      {
        "columns": ["Margin %"],
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
{ "row": 12, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: San pham margin thap

San pham co bien loi nhuan gop duoi 30% — bang chi tiet de review.

```sql
SELECT
    product_code AS "Ma san pham",
    product_name AS "San pham",
    SUM(revenue_net_of_discount) AS "Doanh thu",
    SUM(cogs) AS "Gia von",
    SUM(gross_profit) AS "Loi nhuan gop",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    ) AS "Margin %"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND posting_date >= {{date_range}}]]
GROUP BY product_code, product_name
HAVING ROUND(
    SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
    1
) < 30
ORDER BY "Margin %" ASC
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
      "Gia von": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Loi nhuan gop": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Margin %": {
        "number_style": "decimal",
        "decimals": 1,
        "suffix": "%"
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Margin %"],
        "type": "single",
        "operator": "<",
        "value": 15,
        "color": "#EF8C8C",
        "highlight_row": false
      },
      {
        "columns": ["Margin %"],
        "type": "single",
        "operator": ">=",
        "value": 40,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 12, "col": 9, "size_x": 9, "size_y": 9 }
```

---

#### 📝 Text: Product Profitability Heading

# Phan tich sinh loi theo kenh — Revenue vs Margin % de tim diem toi uu

```json metabase-pos
{ "row": 21, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Product Category Profitability Heatmap

Scatter: moi kenh ban hang la 1 diem — X = Doanh thu, Y = Bien LN %, size = so don hang. Goc phai tren = high-margin + high-revenue (toi uu). Goc trai duoi = low-margin + low-revenue (can review hoac cat).

```sql
SELECT
    channel_name                                                          AS "Kenh ban hang",
    SUM(revenue_net_of_discount)                                          AS "Doanh thu",
    ROUND(
        SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0),
        1
    )                                                                     AS "Bien LN %",
    COUNT(*)                                                              AS "So dong",
    CASE
        WHEN ROUND(SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0), 1) >= 40
            THEN 'High (>=40%)'
        WHEN ROUND(SUM(gross_profit) * 100.0 / NULLIF(SUM(revenue_net_of_discount), 0), 1) >= 25
            THEN 'Medium (25-40%)'
        ELSE 'Low (<25%)'
    END                                                                   AS "Margin Tier"
FROM int_misa_sales_lines
WHERE NOT is_promo_line
  [[AND posting_date >= {{date_range}}]]
GROUP BY channel_name
HAVING SUM(revenue_net_of_discount) > 0
ORDER BY "Doanh thu" DESC
```

```json metabase-viz
{
  "display": "scatter",
  "visualization_settings": {
    "graph.dimensions": ["Kenh ban hang"],
    "graph.metrics": ["Doanh thu", "Bien LN %"],
    "scatter.bubble": "So dong",
    "graph.x_axis.title_text": "Doanh thu (VND)",
    "graph.y_axis.title_text": "Bien loi nhuan (%)",
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Bien LN %": {
        "number_style": "decimal",
        "decimals": 1,
        "suffix": "%"
      }
    }
  }
}
```

```json metabase-pos
{ "row": 22, "col": 0, "size_x": 18, "size_y": 8 }
```

#### 📝 Text: Source & Freshness

**Source:** int_misa_sales_lines + fact_sales · **Cadence:** rolling-30d · **Scope:** NOT is_promo_line
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


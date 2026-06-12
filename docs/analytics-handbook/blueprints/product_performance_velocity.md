---
primary_scope: scope_sales
scope_indicator: "[Cross]"
layer: L3
uses_concepts: [scope_sales, net_revenue, units_sold, velocity_momentum, lifecycle_stage, health_class]
---

# Product Performance & Velocity [Cross] Blueprint

**Design Spec**: [Product Performance](../designs/product_performance.md)

Dashboard theo doi hieu suat + velocity san pham — doanh thu, so luong, xu huong MoM, top/bottom movers, health signals (velocity_momentum + lifecycle_stage tu mart_product_health). Rolling-30d.

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md)
> **Scope:** `scope_sales` · Layer L3 `[Cross]`
> **Sources:** `mart_sku_economics_monthly` (velocity, units_sold, net_revenue, revenue_share_pct), `mart_product_health` (velocity_momentum, lifecycle_stage, health_class), `fact_sales`, `fact_orders`, `dim_products`, `dim_product_types`
>
> **Concepts used:**
> [`scope_sales`](../semantic/segments.md#scope_sales) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`units_sold`](../semantic/metrics.md#units_sold)

## 📂 Collection: Merchandising & Product

### Dashboard: Product Performance & Velocity [Cross]

**Description**: Audience: Analyst / Product Manager. Scope: Cross-segment product sales performance — velocity, revenue, MoM trends, top/bottom movers, health signals (ACCELERATING/DECELERATING). Rolling-30d cadence.

---

#### Filter: Loai san pham

```json metabase-filter
{
  "slug": "product_type",
  "type": "string/="
}
```

---

### 📑 Tab: Tong quan

#### ❓ Question: Chu ky bao cao

```sql
WITH filter_bounds AS (
    SELECT MIN(o.ordered_at)::DATE AS p_start, MAX(o.ordered_at)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
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
    '📅 Ky nay: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Ky truoc: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu ky bao cao"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Overview Heading

# Hieu suat san pham — doanh thu, velocity, va xu huong MoM

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Doanh thu san pham

Hero metric — tong doanh thu san pham this period vs previous period.

```sql
WITH
filter_bounds AS (
    SELECT MIN(o.ordered_at)::DATE AS p_start, MAX(o.ordered_at)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
this_period AS (
    SELECT COALESCE(SUM(s.net_revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(s.net_revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.ordered_at::DATE <  filter_bounds.p_start
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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
    SELECT MIN(o.ordered_at)::DATE AS p_start, MAX(o.ordered_at)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
this_period AS (
    SELECT COALESCE(SUM(s.quantity), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
),
prev_period AS (
    SELECT COALESCE(SUM(s.quantity), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.ordered_at::DATE <  filter_bounds.p_start
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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
    SELECT MIN(o.ordered_at)::DATE AS p_start, MAX(o.ordered_at)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
this_period AS (
    SELECT COUNT(DISTINCT s.product_key) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
),
prev_period AS (
    SELECT COUNT(DISTINCT s.product_key) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.ordered_at::DATE <  filter_bounds.p_start
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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

#### Question: DT trung binh/san pham

Supporting KPI — revenue per distinct product this period vs previous period.

```sql
WITH
filter_bounds AS (
    SELECT MIN(o.ordered_at)::DATE AS p_start, MAX(o.ordered_at)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
),
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT s.product_key) = 0 THEN 0
             ELSE ROUND(SUM(s.net_revenue) / COUNT(DISTINCT s.product_key), 0)
        END as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT s.product_key) = 0 THEN 0
             ELSE ROUND(SUM(s.net_revenue) / COUNT(DISTINCT s.product_key), 0)
        END as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id, filter_bounds
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at::DATE >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND o.ordered_at::DATE <  filter_bounds.p_start
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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

# Xu huong doanh thu + velocity momentum MoM

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Doanh thu san pham theo ngay

Trend doanh thu hang ngay — overlay this month vs last month.

```sql
WITH
this_month AS (
    SELECT
        date(o.ordered_at) as ngay,
        COALESCE(SUM(s.net_revenue), 0) as doanh_thu
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
    GROUP BY date(o.ordered_at)
),
last_month AS (
    SELECT
        date(o.ordered_at) + INTERVAL '30 days' as ngay,
        COALESCE(SUM(s.net_revenue), 0) as doanh_thu
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
    GROUP BY date(o.ordered_at) + INTERVAL '30 days'
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
      "Thang nay": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true },
      "Thang truoc": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 12, "size_y": 6 }
```

#### Question: So luong ban theo ngay

Trend quantity hang ngay — overlay this month vs last month.

```sql
WITH
this_month AS (
    SELECT
        date(o.ordered_at) as ngay,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
    GROUP BY date(o.ordered_at)
),
last_month AS (
    SELECT
        date(o.ordered_at) + INTERVAL '30 days' as ngay,
        COALESCE(SUM(s.quantity), 0) as so_luong
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
    GROUP BY date(o.ordered_at) + INTERVAL '30 days'
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
{ "row": 9, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Contribution Heading

# Dong gop theo loai san pham — ranking va composition

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Doanh thu theo loai san pham

Ranking loai SP theo doanh thu — horizontal bar.

```sql
SELECT
    pt.product_type_name as "Loai san pham",
    COALESCE(SUM(s.net_revenue), 0) as "Doanh thu"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
WHERE o.status != 'CANCELLED'
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  [[AND pt.product_type_name = {{product_type}}]]
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
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 16, "col": 0, "size_x": 9, "size_y": 6 }
```

#### Question: Ty trong doanh thu theo loai san pham

Phan bo % doanh thu theo loai SP — donut chart.

```sql
SELECT
    pt.product_type_name as "Loai san pham",
    COALESCE(SUM(s.net_revenue), 0) as "Doanh thu"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_product_types pt ON s.product_type_key = pt.product_type_key
WHERE o.status != 'CANCELLED'
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  [[AND pt.product_type_name = {{product_type}}]]
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
{ "row": 16, "col": 9, "size_x": 9, "size_y": 6 }
```

---

#### 📝 Text: Source & Freshness

**Source:** fact_sales + fact_orders + mart_product_health · **Cadence:** rolling-30d · **Scope:** scope_sales [Cross]
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: Top & Bottom + Velocity

#### ❓ Question: Chu ky bao cao

```sql
WITH filter_bounds AS (
    SELECT MIN(o.ordered_at)::DATE AS p_start, MAX(o.ordered_at)::DATE AS p_end
    FROM fact_orders o
    JOIN fact_sales s ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
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
    '📅 Ky nay: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Ky truoc: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu ky bao cao"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Top Products Heading

# Top 20 san pham ban chay — focus marketing va stock

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top 20 SP theo doanh thu

Ranking san pham theo revenue — horizontal bar.

```sql
SELECT
    p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END as "San pham",
    COALESCE(SUM(s.net_revenue), 0) as "Doanh thu"
FROM fact_sales s
JOIN fact_orders o ON s.order_id = o.order_id
LEFT JOIN dim_products p ON s.product_key = p.product_key
WHERE o.status != 'CANCELLED'
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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
      "Doanh thu": { "number_style": "currency", "currency": "VND", "decimals": 0, "compact": true }
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
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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
        MIN(p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END) as ten_sp,
        COALESCE(SUM(s.net_revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_products p ON s.product_key = p.product_key
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
    GROUP BY s.product_key
),
prev_period AS (
    SELECT
        s.product_key,
        COALESCE(SUM(s.net_revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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
        MIN(p.product_name || CASE WHEN p.variant_name IS NOT NULL AND p.variant_name != '' THEN ' - ' || p.variant_name ELSE '' END) as ten_sp,
        COALESCE(SUM(s.net_revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    LEFT JOIN dim_products p ON s.product_key = p.product_key
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '30 days'
      AND o.ordered_at < current_date
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
    GROUP BY s.product_key
),
prev_period AS (
    SELECT
        s.product_key,
        COALESCE(SUM(s.net_revenue), 0) as val
    FROM fact_sales s
    JOIN fact_orders o ON s.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
      AND o.ordered_at >= current_date - INTERVAL '60 days'
      AND o.ordered_at < current_date - INTERVAL '30 days'
      [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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

# Velocity — san pham quay nhanh nhat

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
  AND o.ordered_at >= current_date - INTERVAL '30 days'
  AND o.ordered_at < current_date
  [[AND s.product_type_key IN (SELECT product_type_key FROM dim_product_types WHERE product_type_name = {{product_type}})]]
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

#### 📝 Text: Source & Freshness

**Source:** fact_sales + fact_orders + dim_products · **Cadence:** rolling-30d · **Scope:** scope_sales [Cross]
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

---

### 📑 Tab: Health Signals

#### ❓ Question: Chu ky bao cao

```sql
SELECT '📅 Hom nay: ' || strftime(current_date, '%d/%m/%Y') || '  ·  Health signals tu mart_product_health (rolling 24m)' AS "Chu ky bao cao"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Health Overview Heading

# Phan loai suc khoe san pham — velocity_momentum + lifecycle_stage

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Phan bo lifecycle stage

San pham theo lifecycle — bar chart theo giai doan.

```sql
SELECT
    COALESCE(lifecycle_stage, 'UNKNOWN') as "Giai doan",
    COUNT(*) as "So san pham",
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as "Ti trong %"
FROM mart_product_health
WHERE product_key IS NOT NULL
GROUP BY lifecycle_stage
ORDER BY "So san pham" DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Giai doan"],
    "graph.metrics": ["So san pham"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Giai doan vong doi",
    "graph.y_axis.title_text": "So san pham"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 9, "size_y": 5 }
```

#### Question: Phan bo velocity momentum

San pham theo momentum — ACCELERATING / STABLE / DECELERATING.

```sql
SELECT
    COALESCE(velocity_momentum, 'UNKNOWN') as "Momentum",
    COUNT(*) as "So san pham"
FROM mart_product_health
WHERE product_key IS NOT NULL
GROUP BY velocity_momentum
ORDER BY
    CASE velocity_momentum
        WHEN 'ACCELERATING' THEN 1
        WHEN 'STABLE' THEN 2
        WHEN 'DECELERATING' THEN 3
        ELSE 4
    END
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
{ "row": 3, "col": 9, "size_x": 9, "size_y": 5 }
```

---

#### 📝 Text: Accelerating Heading

# San pham ACCELERATING — momentum tang, uu tien stock va marketing

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: San pham ACCELERATING

Top san pham dang tang toc ban — velocity_momentum = ACCELERATING.

```sql
SELECT
    ph.product_name as "San pham",
    COALESCE(ph.abc_class, '?') as "ABC",
    COALESCE(ph.lifecycle_stage, '?') as "Giai doan",
    ROUND(COALESCE(ph.velocity_90d, 0), 2) as "Velocity 90d",
    ROUND(COALESCE(ph.daily_velocity, 0), 2) as "Daily Velocity",
    COALESCE(ph.units_sold, 0) as "Units (thang)",
    ROUND(COALESCE(ph.revenue_share_pct, 0) * 100, 2) as "Revenue Share %",
    COALESCE(ph.health_class, 'N/A') as "Health Class"
FROM mart_product_health ph
WHERE ph.velocity_momentum = 'ACCELERATING'
ORDER BY COALESCE(ph.daily_velocity, 0) DESC
LIMIT 30
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Revenue Share %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#84BB4C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### 📝 Text: Decelerating Heading

# San pham DECELERATING — xu huong giam, can theo doi va can thiep

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: San pham DECELERATING

San pham dang giam toc ban — velocity_momentum = DECELERATING.

```sql
SELECT
    ph.product_name as "San pham",
    COALESCE(ph.abc_class, '?') as "ABC",
    COALESCE(ph.lifecycle_stage, '?') as "Giai doan",
    ROUND(COALESCE(ph.velocity_90d, 0), 2) as "Velocity 90d",
    ROUND(COALESCE(ph.daily_velocity, 0), 2) as "Daily Velocity",
    COALESCE(ph.units_sold, 0) as "Units (thang)",
    ROUND(COALESCE(ph.revenue_share_pct, 0) * 100, 2) as "Revenue Share %",
    COALESCE(ph.health_class, 'N/A') as "Health Class"
FROM mart_product_health ph
WHERE ph.velocity_momentum = 'DECELERATING'
ORDER BY COALESCE(ph.revenue_share_pct, 0) DESC
LIMIT 30
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Revenue Share %"],
        "type": "single",
        "operator": ">",
        "value": 5,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 18, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### 📝 Text: Health Class Heading

# Health classification — velocity x margin (chi ~42 SP co COGS)

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Bang health classification

Phan loai suc khoe day du — STAR / WORKHORSE / QUESTION / DOG / BALANCED.

```sql
SELECT
    ph.product_name as "San pham",
    COALESCE(ph.abc_class, '?') as "ABC",
    COALESCE(ph.health_class, 'N/A') as "Health Class",
    COALESCE(ph.lifecycle_stage, '?') as "Giai doan",
    COALESCE(ph.velocity_momentum, '?') as "Momentum",
    ROUND(COALESCE(ph.velocity_90d, 0), 2) as "Velocity 90d",
    ROUND(COALESCE(ph.realized_margin_pct, 0) * 100, 1) as "Margin %",
    COALESCE(ph.units_sold, 0) as "Units (thang)",
    ROUND(COALESCE(ph.revenue_share_pct, 0) * 100, 2) as "Revenue Share %"
FROM mart_product_health ph
WHERE ph.health_class IS NOT NULL
ORDER BY
    CASE ph.health_class
        WHEN 'STAR'      THEN 1
        WHEN 'WORKHORSE' THEN 2
        WHEN 'BALANCED'  THEN 3
        WHEN 'QUESTION'  THEN 4
        WHEN 'DOG'       THEN 5
        ELSE 6
    END,
    COALESCE(ph.revenue_share_pct, 0) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.column_formatting": [
      {
        "columns": ["Margin %"],
        "type": "single",
        "operator": ">=",
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
{ "row": 27, "col": 0, "size_x": 18, "size_y": 9 }
```

---

#### 📝 Text: Source & Freshness

**Source:** mart_product_health (daily) · velocity_90d tu int_product_velocity_trend · health_class chi cho ~42 SP co COGS · **Cadence:** daily snapshot · **Scope:** all products
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

# US CrossBorder Operations Blueprint [US]

**Scope**: scope_us (`channel_name = 'US'` / `channel_format = 'CrossBorder Fulfillment'`)
**Layer**: L2 - CrossBorder Operations

> **NEW (2026-04-19):** Dashboard rieng cho don US CrossBorder Fulfillment.
> Tach biet hoan toan khoi bao cao Sales vi day la don export/arrangement, khong phai sales thuong.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

Daily monitoring for US CrossBorder fulfillment orders — export arrangements, order tracking, fulfillment status. Special operations for international orders.

## 📂 Collection: Operations > US CrossBorder

> **Database:** Sapo

### Dashboard: Us CrossBorder [US]

**Description**: Daily monitoring of US CrossBorder orders — revenue tracking, order status, fulfillment pipeline. Dynamic period filter covers any date range.

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "thismonth",
  "field_id": 141
}
```

---

### 📑 Tab: Tong quan

#### Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start, '%d/%m/%Y') || ' – ' || strftime(p_end, '%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime((p_start - (p_end - p_start)::INTEGER - 1)::DATE, '%d/%m/%Y') ||
    ' – ' || strftime((p_start - 1)::DATE, '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM filter_bounds
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Don US CrossBorder trong ky

# Don US CrossBorder trong ky

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Net Revenue (US)

US CrossBorder net revenue this period vs previous period.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
),
prev_bounds AS (
    SELECT p_start, p_end,
        (EXTRACT(YEAR FROM p_end)::INTEGER - EXTRACT(YEAR FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM filter_bounds
),
this_period AS (
    SELECT COALESCE(SUM(e.total_us_revenue_excl_vat), 0) AS val
    FROM fact_us_shipment_economics e, filter_bounds
    WHERE e.date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
      AND e.date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
),
prev_period AS (
    SELECT COALESCE(SUM(e.total_us_revenue_excl_vat), 0) AS val
    FROM fact_us_shipment_economics e, prev_bounds
    WHERE e.date_key >= CAST(strftime((prev_bounds.p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE, '%Y%m%d') AS INTEGER)
      AND e.date_key <  CAST(strftime(prev_bounds.p_start, '%Y%m%d') AS INTEGER)
)
SELECT t.val AS "Doanh thu US", p.val AS "Ky truoc" FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Doanh thu US": {
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
{ "row": 3, "col": 0, "size_x": 5, "size_y": 3 }
```

#### Question: Total Orders (US)

US CrossBorder order count this period vs previous period.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
),
prev_bounds AS (
    SELECT p_start, p_end,
        (EXTRACT(YEAR FROM p_end)::INTEGER - EXTRACT(YEAR FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM filter_bounds
),
this_period AS (
    SELECT COUNT(DISTINCT e.order_id) AS val
    FROM fact_us_shipment_economics e, filter_bounds
    WHERE e.date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
      AND e.date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
),
prev_period AS (
    SELECT COUNT(DISTINCT e.order_id) AS val
    FROM fact_us_shipment_economics e, prev_bounds
    WHERE e.date_key >= CAST(strftime((prev_bounds.p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE, '%Y%m%d') AS INTEGER)
      AND e.date_key <  CAST(strftime(prev_bounds.p_start, '%Y%m%d') AS INTEGER)
)
SELECT t.val AS "Total Orders", p.val AS "Ky truoc" FROM this_period t, prev_period p
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 5, "size_x": 4, "size_y": 3 }
```

#### Question: AOV (US)

Average order value for US CrossBorder this period vs previous period.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
),
prev_bounds AS (
    SELECT p_start, p_end,
        (EXTRACT(YEAR FROM p_end)::INTEGER - EXTRACT(YEAR FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM filter_bounds
),
this_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT e.order_id) = 0 THEN 0
             ELSE ROUND(SUM(e.total_us_revenue_excl_vat) / COUNT(DISTINCT e.order_id), 0) END AS val
    FROM fact_us_shipment_economics e, filter_bounds
    WHERE e.date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
      AND e.date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
),
prev_period AS (
    SELECT
        CASE WHEN COUNT(DISTINCT e.order_id) = 0 THEN 0
             ELSE ROUND(SUM(e.total_us_revenue_excl_vat) / COUNT(DISTINCT e.order_id), 0) END AS val
    FROM fact_us_shipment_economics e, prev_bounds
    WHERE e.date_key >= CAST(strftime((prev_bounds.p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE, '%Y%m%d') AS INTEGER)
      AND e.date_key <  CAST(strftime(prev_bounds.p_start, '%Y%m%d') AS INTEGER)
)
SELECT t.val AS "AOV", p.val AS "Ky truoc" FROM this_period t, prev_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "AOV": {
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
{ "row": 3, "col": 9, "size_x": 4, "size_y": 3 }
```

#### Question: Unique Customers (US)

Distinct customers ordering via US channel in selected period.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
),
prev_bounds AS (
    SELECT p_start, p_end,
        (EXTRACT(YEAR FROM p_end)::INTEGER - EXTRACT(YEAR FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM filter_bounds
),
this_period AS (
    SELECT COUNT(DISTINCT fo.customer_key) AS val
    FROM fact_us_shipment_economics e
    JOIN fact_orders fo ON e.order_id = fo.order_id, filter_bounds
    WHERE e.date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
      AND e.date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
),
prev_period AS (
    SELECT COUNT(DISTINCT fo.customer_key) AS val
    FROM fact_us_shipment_economics e
    JOIN fact_orders fo ON e.order_id = fo.order_id, prev_bounds
    WHERE e.date_key >= CAST(strftime((prev_bounds.p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE, '%Y%m%d') AS INTEGER)
      AND e.date_key <  CAST(strftime(prev_bounds.p_start, '%Y%m%d') AS INTEGER)
)
SELECT t.val AS "Khach hang", p.val AS "Ky truoc" FROM this_period t, prev_period p
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 13, "size_x": 5, "size_y": 3 }
```

#### 📝 Text: Trang thai don va fulfillment

# Trang thai don va fulfillment

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Status (US)

Distribution of order statuses for US CrossBorder in selected period.

```sql
SELECT
    fact_orders.status AS "Trang thai",
    COUNT(DISTINCT fact_orders.order_id) AS "So don"
FROM fact_orders
JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
WHERE ch.channel_name = 'US'
  [[AND {{date_range}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Trang thai"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"]
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 9, "size_y": 5 }
```

#### Question: Fulfillment Status (US)

Distribution of fulfillment statuses for US CrossBorder in selected period.

```sql
SELECT
    COALESCE(fact_orders.fulfillment_status, 'Unknown') AS "Fulfillment",
    COUNT(DISTINCT fact_orders.order_id) AS "So don"
FROM fact_orders
JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
WHERE ch.channel_name = 'US'
  [[AND {{date_range}}]]
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Fulfillment"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#88BF4D"]
  }
}
```

```json metabase-pos
{ "row": 7, "col": 9, "size_x": 9, "size_y": 5 }
```

#### 📝 Text: Xu huong theo ngay trong ky

# Xu huong theo ngay trong ky

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Revenue & Orders Trend (US)

Daily revenue and order count trend within selected period.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
)
SELECT
    make_date((e.date_key/10000)::INTEGER, ((e.date_key%10000)/100)::INTEGER, (e.date_key%100)::INTEGER) AS "Ngay",
    SUM(e.total_us_revenue_excl_vat) AS "Doanh thu US",
    COUNT(DISTINCT e.order_id) AS "So don"
FROM fact_us_shipment_economics e, filter_bounds fb
WHERE e.date_key >= CAST(strftime(fb.p_start, '%Y%m%d') AS INTEGER)
  AND e.date_key <= CAST(strftime(fb.p_end, '%Y%m%d') AS INTEGER)
GROUP BY e.date_key
ORDER BY e.date_key
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Doanh thu US", "So don"],
    "graph.colors": ["#509EE3", "#EF8C8C"],
    "series_settings": {
      "Doanh thu US": { "display": "bar" },
      "So don": { "display": "line", "axis": "right" }
    },
    "column_settings": {
      "Doanh thu US": {
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
{ "row": 13, "col": 0, "size_x": 18, "size_y": 6 }
```

#### 📝 Text: Danh sach don US trong ky

# Danh sach don US trong ky

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: US Orders List

Detailed list of US CrossBorder orders in selected period.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch2 ON fact_orders.channel_key = ch2.channel_key
    WHERE ch2.channel_name = 'US'
      [[AND {{date_range}}]]
)
SELECT
    e.order_code AS "Ma don",
    make_date((e.date_key/10000)::INTEGER, ((e.date_key%10000)/100)::INTEGER, (e.date_key%100)::INTEGER) AS "Ngay",
    COALESCE(c.full_name, 'Unknown') AS "Khach hang",
    e.total_us_revenue_excl_vat AS "Doanh thu US",
    fo.status AS "Trang thai",
    fo.fulfillment_status AS "Fulfillment",
    fo.payment_status AS "Thanh toan",
    CASE WHEN e.has_unpriced_sku THEN 'Thieu gia' ELSE '' END AS "Data Quality"
FROM fact_us_shipment_economics e
JOIN fact_orders fo ON e.order_id = fo.order_id
LEFT JOIN dim_customers c ON fo.customer_key = c.customer_key, filter_bounds fb
WHERE e.date_key >= CAST(strftime(fb.p_start, '%Y%m%d') AS INTEGER)
  AND e.date_key <= CAST(strftime(fb.p_end, '%Y%m%d') AS INTEGER)
ORDER BY fo.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "[\"name\",\"Ma don\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "url",
          "linkTemplate": "https://detailview.lan.fwg.vn/orders/{{Ma don}}"
        }
      }
    }
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 12 }
```

#### 📝 Text: Canh bao thieu gia

# Canh bao thieu gia

```json metabase-pos
{ "row": 32, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Don thieu gia US (trong ky)

So don trong ky co SKU chua co trong price list US.

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
)
SELECT
    COUNT(*) AS "Don thieu gia"
FROM fact_us_shipment_economics e, filter_bounds fb
WHERE e.date_key >= CAST(strftime(fb.p_start, '%Y%m%d') AS INTEGER)
  AND e.date_key <= CAST(strftime(fb.p_end, '%Y%m%d') AS INTEGER)
  AND e.has_unpriced_sku = TRUE
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "scalar.switch_positive_negative": true } }
```

```json metabase-pos
{ "row": 33, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: SKU chua co gia (trong ky)

```sql
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    JOIN dim_channels ch ON fact_orders.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      [[AND {{date_range}}]]
)
SELECT
    l.sku                              AS "SKU",
    COUNT(DISTINCT l.order_id)         AS "So don",
    SUM(l.quantity)                    AS "So luong"
FROM int_us_shipment_line_prices l, filter_bounds fb
WHERE l.is_price_missing = TRUE
  AND l.date_key >= CAST(strftime(fb.p_start, '%Y%m%d') AS INTEGER)
  AND l.date_key <= CAST(strftime(fb.p_end, '%Y%m%d') AS INTEGER)
GROUP BY l.sku
ORDER BY COUNT(DISTINCT l.order_id) DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "card.title": "SKU chưa có giá — cần bổ sung vào price list"
  }
}
```

```json metabase-pos
{ "row": 36, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### 📝 Text: Source & Freshness

**Source:** fact_us_shipment_economics · **Cadence:** daily · **Scope:** US CrossBorder non-cancelled · **Caveats:** Export arrangement
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

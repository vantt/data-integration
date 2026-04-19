# B2B Daily Sales Blueprint [B2B]

**Scope**: scope_b2b (`customer_type IN ('WHOLESALE', 'PARTNER')` + `is_sales_channel = true`)
**Layer**: L2 - B2B Operations

> **NEW (2026-04-19):** Dashboard mới cho B2B business line.
> Tách biệt khỏi retail operations để tránh trộn lẫn dữ liệu.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

Daily monitoring for wholesale and partner orders — revenue, order volume, key accounts, payment status. Focus on B2B-specific metrics.

## 📂 Collection: Operations > B2B Operations

> **Database:** Sapo DuckDB

### Dashboard: B2B Daily Sales [B2B]

**Description**: Daily monitoring of B2B sales (WHOLESALE, PARTNER) — revenue KPIs, top accounts, payment status, order breakdown. 2 tabs: Tong quan, Chi tiet don hang.

---

### 📑 Tab: Tong quan

#### 📝 Text: Doanh thu B2B hom nay — khach si va doi tac

# Doanh thu B2B hom nay — khach si va doi tac

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Net Revenue (B2B)

B2B revenue today vs yesterday.

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date THEN o.net_revenue END), 0) as "Net Revenue",
    COALESCE(SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.net_revenue END), 0) as "Hom qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "dod",
        "type": "anotherColumn",
        "column": "Hom qua",
        "label": "vs hom qua"
      }
    ],
    "column_settings": {
      "Net Revenue": {
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
{ "row": 1, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Total Orders (B2B)

B2B order count today vs yesterday.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END) as "Total Orders",
    COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END) as "Hom qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "dod",
        "type": "anotherColumn",
        "column": "Hom qua",
        "label": "vs hom qua"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 1, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: AOV (B2B)

B2B average order value — typically higher than retail.

```sql
SELECT
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.order_timestamp) = current_date THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date THEN o.order_id END), 0
         ) END as "AOV",
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.order_timestamp) = current_date - INTERVAL '1 day' THEN o.order_id END), 0
         ) END as "Hom qua"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) >= current_date - INTERVAL '1 day'
  AND date(o.order_timestamp) <= current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "dod",
        "type": "anotherColumn",
        "column": "Hom qua",
        "label": "vs hom qua"
      }
    ],
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
{ "row": 1, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: Unique Customers (B2B)

Number of B2B customers ordering today.

```sql
SELECT COUNT(DISTINCT o.customer_key) as "Khach B2B"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 1, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Phan bo theo loai khach va kenh

# Phan bo theo loai khach va kenh

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Revenue by Customer Type

Wholesale vs Partner breakdown.

```sql
SELECT
    c.customer_type as "Loai khach",
    COUNT(DISTINCT o.order_id) as "Don hang",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY c.customer_type
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Loai khach"],
    "graph.metrics": ["Doanh thu", "Don hang"],
    "graph.colors": ["#509EE3", "#A989C5"],
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
{ "row": 5, "col": 0, "size_x": 9, "size_y": 5 }
```

#### Question: Revenue by Channel (B2B)

Which channels B2B customers use.

```sql
SELECT
    ch.channel_name as "Kenh",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY ch.channel_name
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Kenh"],
    "graph.metrics": ["Doanh thu"],
    "graph.colors": ["#509EE3"],
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
{ "row": 5, "col": 9, "size_x": 9, "size_y": 5 }
```

---

#### 📝 Text: Top khach hang B2B hom nay

# Top khach hang B2B hom nay

```json metabase-pos
{ "row": 10, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top B2B Customers Today

Top 10 B2B customers by revenue today.

```sql
SELECT
    c.full_name as "Khach hang",
    c.customer_type as "Loai",
    COUNT(DISTINCT o.order_id) as "Don hang",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY c.full_name, c.customer_type
ORDER BY 4 DESC
LIMIT 10
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
    }
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 6 }
```

---

### 📑 Tab: Chi tiet don hang

#### 📝 Text: Danh sach don B2B hom nay

# Danh sach don B2B hom nay

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: B2B Orders List

Full order list for B2B customers today.

```sql
SELECT
    o.order_code as "Ma don",
    c.full_name as "Khach hang",
    c.customer_type as "Loai",
    ch.channel_name as "Kenh",
    o.net_revenue as "Doanh thu",
    o.discount_amount as "Chiet khau",
    o.status as "Trang thai",
    o.payment_status as "Thanh toan",
    o.order_timestamp as "Thoi gian"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = current_date
  AND c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.cell_height": "compact",
    "column_settings": {
      "Doanh thu": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Chiet khau": {
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
{ "row": 1, "col": 0, "size_x": 18, "size_y": 12 }
```

---

#### 📝 Text: Source & Freshness

Source: fact_orders · Updated real-time · **Scope: B2B only (customer_type IN ('WHOLESALE', 'PARTNER'))**

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 18, "size_y": 1 }
```

---

> **Scope Note:** Tất cả queries trong blueprint này filter `customer_type IN ('WHOLESALE', 'PARTNER')`. Retail orders được track trong **Daily Sales [Retail]** blueprint.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

---
primary_scope: scope_b2b
scope_indicator: "[B2B]"
layer: L2
uses_concepts: [scope_b2b, net_revenue, orders_count]
---

# B2B Orders Tracking Blueprint [B2B]

## Segmentation Scope

> **Scope:** `scope_b2b` · Layer 2 (B2B Operations) · Suffix `[B2B]`
> **Why:** B2B order tracking monitors WHOLESALE and PARTNER orders — payment status, order age, key accounts. Retail orders are excluded.
> **Ref:** [segments.md#scope_b2b](../semantic/segments.md#scope_b2b)

All SQL: `WHERE scope_b2b`.

**Scope**: scope_b2b (`customer_type IN ('WHOLESALE', 'PARTNER')` + `is_sales_channel = true`)
**Layer**: L2 - B2B Operations

> **NEW (2026-04-19):** Order tracking cho B2B business line.
> Focus: payment status, fulfillment, outstanding receivables.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

Track B2B order lifecycle — payment collection, fulfillment status, outstanding amounts. Key for accounts receivable management.

## 📂 Collection: Operations > B2B Operations

> **Database:** Sapo

### Dashboard: B2B Orders Tracking [B2B]

**Description**: Track B2B order payment and fulfillment status — unpaid orders, outstanding amounts, payment aging. 2 tabs: Cong no, Giao hang.

#### Filter: date_range

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past1months",
  "field_id": 848
}
```

---

### 📑 Tab: Cong no

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
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

#### 📝 Text: Tinh hinh cong no B2B

# Tinh hinh cong no B2B

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Outstanding Amount (B2B)

Total unpaid amount from B2B customers.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT
    COALESCE(SUM(o.net_revenue), 0) as "Cong no"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.payment_status IN ('UNPAID', 'PARTIAL')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Cong no": {
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
{ "row": 4, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Unpaid Orders Count (B2B)

Number of B2B orders awaiting payment.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT COUNT(DISTINCT o.order_id) as "Don chua thanh toan"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.payment_status IN ('UNPAID', 'PARTIAL')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: Partial Payment Orders (B2B)

Orders with partial payment received.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT COUNT(DISTINCT o.order_id) as "Thanh toan mot phan"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.payment_status = 'PARTIAL'
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: Avg Days Outstanding (B2B)

Average days since order for unpaid B2B orders.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT
    ROUND(AVG(DATEDIFF('day', date(o.ordered_at), current_date)), 1) as "Ngay trung binh"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.payment_status IN ('UNPAID', 'PARTIAL')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Phan tich tuoi cong no

# Phan tich tuoi cong no

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Aging Analysis (B2B)

Outstanding amounts by age bucket.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT
    CASE
        WHEN DATEDIFF('day', date(o.ordered_at), current_date) <= 7 THEN '0-7 ngay'
        WHEN DATEDIFF('day', date(o.ordered_at), current_date) <= 14 THEN '8-14 ngay'
        WHEN DATEDIFF('day', date(o.ordered_at), current_date) <= 30 THEN '15-30 ngay'
        ELSE '> 30 ngay'
    END as "Tuoi no",
    COUNT(DISTINCT o.order_id) as "So don",
    SUM(o.net_revenue) as "Cong no"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.payment_status IN ('UNPAID', 'PARTIAL')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
GROUP BY 1
ORDER BY CASE "Tuoi no" WHEN '0-7 ngay' THEN 1 WHEN '8-14 ngay' THEN 2 WHEN '15-30 ngay' THEN 3 ELSE 4 END
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Tuoi no"],
    "graph.metrics": ["Cong no"],
    "graph.colors": ["#EF8C8C"],
    "column_settings": {
      "Cong no": {
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
{ "row": 9, "col": 0, "size_x": 9, "size_y": 5 }
```

#### Question: Outstanding by Customer Type

Wholesale vs Partner outstanding breakdown.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT
    c.customer_type as "Loai khach",
    COUNT(DISTINCT o.order_id) as "So don",
    SUM(o.net_revenue) as "Cong no"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.payment_status IN ('UNPAID', 'PARTIAL')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
GROUP BY c.customer_type
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Loai khach",
    "pie.metric": "Cong no",
    "column_settings": {
      "Cong no": {
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
{ "row": 9, "col": 9, "size_x": 9, "size_y": 5 }
```

---

#### 📝 Text: Top khach hang cong no

# Top khach hang cong no

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Top Customers by Outstanding

Top 10 B2B customers with highest outstanding amounts.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT
    c.full_name as "Khach hang",
    c.customer_type as "Loai",
    COUNT(DISTINCT o.order_id) as "Don chua TT",
    SUM(o.net_revenue) as "Cong no",
    MIN(date(o.ordered_at)) as "Don cu nhat"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.payment_status IN ('UNPAID', 'PARTIAL')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
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
      "Cong no": {
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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** rolling-30d · **Scope:** customer_type IN ('WHOLESALE','PARTNER') · **Caveats:** AR aging window
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Giao hang

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
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

#### 📝 Text: Tinh trang giao hang B2B

# Tinh trang giao hang B2B

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Pending Fulfillment (B2B)

B2B orders awaiting fulfillment.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT COUNT(DISTINCT o.order_id) as "Cho giao hang"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.fulfillment_status IN ('PENDING', 'PROCESSING')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: In Transit (B2B)

B2B orders currently in transit.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT COUNT(DISTINCT o.order_id) as "Dang giao"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.fulfillment_status = 'SHIPPED'
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 3 }
```

#### Question: Delivered Today (B2B)

B2B orders delivered today.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT COUNT(DISTINCT o.order_id) as "Giao hom nay"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.fulfillment_status = 'DELIVERED'
  AND date(o.updated_at) = current_date
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 3 }
```

---

#### 📝 Text: Don hang cho xu ly

# Don hang cho xu ly

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Pending B2B Orders List

List of B2B orders pending fulfillment.

```sql
WITH filter_bounds AS (
    SELECT MIN(ordered_at)::DATE AS p_start,
           MAX(ordered_at)::DATE AS p_end
    FROM fact_orders
    WHERE status NOT IN ('CANCELLED', 'Voided')
      [[AND {{date_range}}]]
)
SELECT
    o.order_code as "Ma don",
    c.full_name as "Khach hang",
    c.customer_type as "Loai",
    o.net_revenue as "Gia tri",
    o.fulfillment_status as "Giao hang",
    o.payment_status as "Thanh toan",
    o.ordered_at as "Ngay dat",
    DATEDIFF('day', date(o.ordered_at), current_date) as "So ngay"
FROM fact_orders o, filter_bounds
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type IN ('WHOLESALE', 'PARTNER')
  AND o.channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
  AND o.fulfillment_status IN ('PENDING', 'PROCESSING', 'SHIPPED')
  AND o.status NOT IN ('CANCELLED', 'Voided')
  AND o.ordered_at::DATE >= filter_bounds.p_start
  AND o.ordered_at::DATE <= filter_bounds.p_end
ORDER BY o.ordered_at ASC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "table.cell_height": "compact",
    "column_settings": {
      "Gia tri": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
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
{ "row": 7, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Source & Freshness

Source: fact_orders · Updated real-time · **Scope: B2B only (customer_type IN ('WHOLESALE', 'PARTNER'))**

```json metabase-pos
{ "row": 17, "col": 0, "size_x": 18, "size_y": 1 }
```

---

> **Scope Note:** Tất cả queries trong blueprint này filter `customer_type IN ('WHOLESALE', 'PARTNER')`. Retail orders được track trong **Orders Tracking [Retail]** blueprint.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

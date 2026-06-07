---
primary_scope: scope_b2b
scope_indicator: "[B2B]"
layer: L2
uses_concepts: [scope_b2b, net_revenue, orders_count, aov]
---

# B2B Daily Sales Blueprint [B2B]

## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_b2b` · Layer L2 `[B2B]` · [`segments.md#scope_b2b`](../semantic/segments.md#scope_b2b)
> **Why:** B2B daily monitoring covers WHOLESALE and PARTNER orders only. AOV ~2.5M VND; discount = fixed wholesale pricing, not promotion.
>
> **Concepts used:**
> [`scope_b2b`](../semantic/segments.md#scope_b2b) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`orders_count`](../semantic/metrics.md#orders_count) · [`aov`](../semantic/metrics.md#aov)

All SQL: `WHERE scope_b2b`. Do not re-derive the scope inline — `scope_b2b` already encodes customer segment, channel, and cancellation filters.
## 📂 Collection: Operations > B2B Operations

> **Database:** Sapo

### Dashboard: B2B Daily Sales [B2B]

**Description**: Daily monitoring of B2B sales (WHOLESALE, PARTNER) — revenue KPIs, top accounts, payment status, order breakdown. 2 tabs: Tong quan, Chi tiet don hang.

---

### 📑 Tab: Tong quan

#### 📝 Text: Doanh thu B2B hom nay — khach si va doi tac

# Doanh thu B2B hom nay — khach si va doi tac

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Net Revenue (B2B)

B2B revenue today vs yesterday.

```sql
SELECT
    COALESCE(SUM(CASE WHEN date(o.ordered_at) = current_date THEN o.net_revenue END), 0) as "Net Revenue",
    COALESCE(SUM(CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.net_revenue END), 0) as "Hom qua"
FROM fact_orders o
WHERE date(o.ordered_at) >= current_date - INTERVAL '1 day'
  AND date(o.ordered_at) <= current_date
  AND o.scope_b2b
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
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
{ "row": 4, "col": 0, "size_x": 6, "size_y": 3 }
```

#### Question: Total Orders (B2B)

B2B order count today vs yesterday.

```sql
SELECT
    COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date THEN o.order_id END) as "Total Orders",
    COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.order_id END) as "Hom qua"
FROM fact_orders o
WHERE date(o.ordered_at) >= current_date - INTERVAL '1 day'
  AND date(o.ordered_at) <= current_date
  AND o.scope_b2b
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 4, "size_y": 3 }
```

#### Question: AOV (B2B)

B2B average order value — typically higher than retail.

```sql
SELECT
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.ordered_at) = current_date THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date THEN o.order_id END), 0
         ) END as "AOV",
    CASE WHEN COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.order_id END) = 0 THEN 0
         ELSE ROUND(
            SUM(CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.net_revenue END)
            / COUNT(DISTINCT CASE WHEN date(o.ordered_at) = current_date - INTERVAL '1 day' THEN o.order_id END), 0
         ) END as "Hom qua"
FROM fact_orders o
WHERE date(o.ordered_at) >= current_date - INTERVAL '1 day'
  AND date(o.ordered_at) <= current_date
  AND o.scope_b2b
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
{ "row": 4, "col": 10, "size_x": 4, "size_y": 3 }
```

#### Question: Unique Customers (B2B)

Number of B2B customers ordering today.

```sql
SELECT COUNT(DISTINCT o.customer_key) as "Khach B2B"
FROM fact_orders o
WHERE date(o.ordered_at) = current_date
  AND o.scope_b2b
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 4, "col": 14, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Phan bo theo loai khach va kenh

# Phan bo theo loai khach va kenh

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
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
WHERE date(o.ordered_at) = current_date
  AND o.scope_b2b
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
{ "row": 9, "col": 0, "size_x": 9, "size_y": 5 }
```

#### Question: Revenue by Channel (B2B)

Which channels B2B customers use.

```sql
SELECT
    ch.channel_name as "Kenh",
    SUM(o.net_revenue) as "Doanh thu"
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.ordered_at) = current_date
  AND o.scope_b2b
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
{ "row": 9, "col": 9, "size_x": 9, "size_y": 5 }
```

---

#### 📝 Text: Top khach hang B2B hom nay

# Top khach hang B2B hom nay

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
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
WHERE date(o.ordered_at) = current_date
  AND o.scope_b2b
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
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_customers · **Cadence:** daily · **Scope:** `scope_b2b`
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Chi tiet don hang


#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') || '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y') AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Danh sach don B2B hom nay

# Danh sach don B2B hom nay

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
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
    o.ordered_at as "Thoi gian"
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.ordered_at) = current_date
  AND o.scope_b2b
ORDER BY o.ordered_at DESC
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
{ "row": 3, "col": 0, "size_x": 18, "size_y": 12 }
```

---

#### 📝 Text: Source & Freshness

Source: fact_orders · Updated real-time · **Scope: `scope_b2b`**

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 1 }
```

---

> **Scope Note:** Tất cả queries trong blueprint này filter `scope_b2b`. Retail orders được track trong **Daily Sales [Retail]** blueprint.
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md)

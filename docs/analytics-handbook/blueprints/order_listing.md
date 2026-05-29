# Blueprint: Order Listing [Retail]

**Design Spec**: [Order Listing](../designs/order_listing.md)
**Playbook**: [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

> **Target Collection:** `Operations` > `Daily Monitoring`
> **Role:** Sales Ops, Store Manager, Data Team
> **Archetype:** Operational Cockpit

## 📂 Collection: Operations > Daily Monitoring

Dashboard đối soát đơn hàng — xác minh tính đúng đắn và đầy đủ của dữ liệu BI so với Sapo.

---

### 🖥️ Dashboard: Order Listing [Retail]

**Description**: Công cụ đối soát đơn hàng — Reconciliation Checklist + Data Freshness + KPI DoD + phân bổ (donut/bar) + cảnh báo bất thường + chi tiết đơn. 3 tabs (Today / Yesterday / By Date) đồng bộ hoàn toàn — chỉ khác date predicate.

---

### Tab: Today

#### ❓ Question: Chu kỳ báo cáo

```sql
SELECT '📅 Chu kỳ: Theo filter được chọn (không cố định)'
  AS "Chu kỳ báo cáo"
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Reconciliation Checklist

## 🔍 Đối chiếu BI ↔ Sapo — 5 bước

1. **So Total Orders** với Sapo Admin > Đơn hàng cùng ngày (bao gồm cả CANCELLED).
2. **So Net Revenue** và **Total Collected** với cùng bộ lọc.
3. **Kiểm tra DoD arrow** — đỏ/bất thường → cần điều tra ngay.
4. **Quét Flagged Orders** — bất kỳ dòng nào cũng cần xác minh Sapo.
5. **Lệch > 1 đơn?** Mở Order Detail List, search order code trên Sapo → báo Data Team nếu là ingestion gap.

```json metabase-pos
{"row": 2, "col":0, "size_x":15, "size_y":2}
```

#### Question: Data Freshness

Tuổi của dữ liệu — xanh nếu < 120 phút, cam 120-360 phút, đỏ > 360 phút. Nếu > 120 phút, dừng reconciliation và kiểm tra Dagster trước.

```sql
SELECT
    CAST(date_diff('minute', MAX(updated_at), now()) AS INTEGER) AS "Phút kể từ lần cập nhật cuối"
FROM fact_orders
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Phút kể từ lần cập nhật cuối"
  }
}
```

```json metabase-pos
{"row": 2, "col":15, "size_x":3, "size_y":2}
```

---

#### 📝 Text: Section 1 — Tổng quan

### ▸ Tổng quan đơn hàng — số cần đối soát với Sapo

```json metabase-pos
{"row": 4, "col":0, "size_x":18, "size_y":1}
```

#### Question: Total Orders

```sql
WITH current_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
),
previous_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT c.val as "Total Orders", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom qua"
      }
    ]
  }
}
```

```json metabase-pos
{"row": 5, "col":0, "size_x":6, "size_y":4}
```

#### Question: Net Revenue

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Net Revenue", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom qua"
      }
    ],
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{"row": 5, "col":6, "size_x":4, "size_y":4}
```

#### Question: Total Collected

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Total Collected", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom qua"
      }
    ],
    "column_settings": {
      "Total Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{"row": 5, "col":10, "size_x":4, "size_y":4}
```

#### Question: Gross Revenue

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Gross Revenue", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom qua"
      }
    ],
    "column_settings": {
      "Gross Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{"row": 5, "col":14, "size_x":4, "size_y":4}
```

#### Question: Total Discount

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Total Discount", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom qua"
      }
    ],
    "column_settings": {
      "Total Discount": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{"row": 9, "col":0, "size_x":6, "size_y":4}
```

#### Question: Cancelled Orders

```sql
WITH current_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
      AND status = 'CANCELLED'
),
previous_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status = 'CANCELLED'
)
SELECT c.val as "Cancelled", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom qua"
      }
    ]
  }
}
```

```json metabase-pos
{"row": 9, "col":6, "size_x":6, "size_y":4}
```

#### Question: Returns

```sql
WITH current_period AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date
),
previous_period AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
)
SELECT c.val as "Returns", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom qua"
      }
    ]
  }
}
```

```json metabase-pos
{"row": 9, "col":12, "size_x":6, "size_y":4}
```

---

#### 📝 Text: Section 2 — Phân bổ

### ▸ Phân bổ theo chiều — phát hiện lệch trạng thái, thanh toán, kênh

```json metabase-pos
{"row": 13, "col":0, "size_x":18, "size_y":1}
```

#### Question: Orders by Status

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{"row": 14, "col":0, "size_x":6, "size_y":6}
```

#### Question: Orders by Payment Status

```sql
SELECT
    payment_status as "Payment Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{"row": 14, "col":6, "size_x":6, "size_y":6}
```

#### Question: Orders by Channel

```sql
SELECT
    COALESCE(c.channel_name, 'Unknown') as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue"
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{"row": 14, "col":12, "size_x":6, "size_y":6}
```

---

#### 📝 Text: Section 3 — Cảnh báo

### ▸ Đơn bất thường — cần mở Sapo xác minh từng dòng

```json metabase-pos
{"row": 20, "col":0, "size_x":18, "size_y":1}
```

#### Question: Flagged Orders

```sql
SELECT
    o.order_code as "Order Code",
    o.status as "Status",
    COALESCE(ch.channel_name, 'Unknown') as "Channel",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.total_collected as "Collected",
    CASE
        WHEN o.total_collected = 0 AND o.discount_amount > 0 THEN '100% Discount'
        WHEN o.net_revenue < 0 THEN 'Negative Revenue'
        WHEN o.discount_amount > o.gross_revenue THEN 'Discount > Gross'
        WHEN o.status = 'COMPLETED' AND o.payment_status != 'PAID' THEN 'Completed but Unpaid'
        WHEN o.payment_status = 'REFUNDED' THEN 'Refunded'
    END as "Flag"
FROM fact_orders o
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = current_date
  AND (
    (o.total_collected = 0 AND o.discount_amount > 0)
    OR o.net_revenue < 0
    OR o.discount_amount > o.gross_revenue
    OR (o.status = 'COMPLETED' AND o.payment_status != 'PAID')
    OR o.payment_status = 'REFUNDED'
  )
ORDER BY o.discount_amount DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{"row": 21, "col":0, "size_x":18, "size_y":5}
```

---

#### 📝 Text: Section 4 — Chi tiết

### ▸ Chi tiết đơn hàng — search order code trên Sapo nếu lệch

```json metabase-pos
{"row": 26, "col":0, "size_x":18, "size_y":1}
```

#### Question: Order Detail List

```sql
SELECT
    o.order_id as "order_id",
    o.order_code as "Order Code",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.tax_amount as "Tax",
    o.total_collected as "Collected",
    COALESCE(ch.channel_name, 'Unknown') as "Channel",
    o.payment_status as "Payment",
    o.fulfillment_status as "Fulfillment",
    c.full_name as "Customer",
    c.phone as "Phone",
    bl.branch_location_name as "Store"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
LEFT JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE date(o.order_timestamp) = current_date
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "table.columns": [
      {"name": "order_id", "enabled": false}
    ],
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Tax": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" },
      "[\"name\",\"Order Code\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "dashboard",
          "targetId": 38,
          "parameterMapping": {
            "order_id": {
              "source": { "type": "column", "id": "order_id", "name": "order_id" },
              "target": { "type": "parameter", "id": "order_id" },
              "id": "order_id"
            }
          }
        }
      }
    }
  }
}
```

```json metabase-pos
{"row": 27, "col":0, "size_x":18, "size_y":10}
```

---

#### 📝 Text: Footer — Source & Escalation

Source: `fact_orders` · dbt updates every 10 min via Dagster incremental job · Filter: `status NOT IN ('CANCELLED', 'Voided')` for revenue KPIs · Playbook: [orders_list_reconciliation](../playbooks/orders_list_reconciliation.md) · For help: #data-team

```json metabase-pos
{"row": 37, "col":0, "size_x":18, "size_y":1}
```


---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_* · **Cadence:** rolling-30d · **Scope:** Period filter
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: Yesterday


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

#### 📝 Text: Reconciliation Checklist

## 🔍 Đối chiếu BI ↔ Sapo — 5 bước

1. **So Total Orders** với Sapo Admin > Đơn hàng cùng ngày (bao gồm cả CANCELLED).
2. **So Net Revenue** và **Total Collected** với cùng bộ lọc.
3. **Kiểm tra DoD arrow** — đỏ/bất thường → cần điều tra ngay.
4. **Quét Flagged Orders** — bất kỳ dòng nào cũng cần xác minh Sapo.
5. **Lệch > 1 đơn?** Mở Order Detail List, search order code trên Sapo → báo Data Team nếu là ingestion gap.

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 15, "size_y": 2 }
```

#### Question: Data Freshness

Tuổi của dữ liệu — xanh nếu < 120 phút, cam 120-360 phút, đỏ > 360 phút. Nếu > 120 phút, dừng reconciliation và kiểm tra Dagster trước.

```sql
SELECT
    CAST(date_diff('minute', MAX(updated_at), now()) AS INTEGER) AS "Phút kể từ lần cập nhật cuối"
FROM fact_orders
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Phút kể từ lần cập nhật cuối"
  }
}
```

```json metabase-pos
{ "row": 0, "col": 15, "size_x": 3, "size_y": 2 }
```

---

#### 📝 Text: Section 1 — Tổng quan

### ▸ Tổng quan đơn hàng — số cần đối soát với Sapo

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Total Orders

```sql
WITH current_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
),
previous_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
)
SELECT c.val as "Total Orders", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 6, "size_y": 4 }
```

#### Question: Net Revenue

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Net Revenue", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 4, "size_y": 4 }
```

#### Question: Total Collected

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Total Collected", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Total Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 10, "size_x": 4, "size_y": 4 }
```

#### Question: Gross Revenue

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Gross Revenue", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Gross Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 14, "size_x": 4, "size_y": 4 }
```

#### Question: Total Discount

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Total Discount", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Total Discount": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 6, "size_y": 4 }
```

#### Question: Cancelled Orders

```sql
WITH current_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
      AND status = 'CANCELLED'
),
previous_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
      AND status = 'CANCELLED'
)
SELECT c.val as "Cancelled", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 6, "size_x": 6, "size_y": 4 }
```

#### Question: Returns

```sql
WITH current_period AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
),
previous_period AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE date(order_timestamp) = current_date - INTERVAL '2 days'
)
SELECT c.val as "Returns", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 12, "size_x": 6, "size_y": 4 }
```

---

#### 📝 Text: Section 2 — Phân bổ

### ▸ Phân bổ theo chiều — phát hiện lệch trạng thái, thanh toán, kênh

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Status

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Orders by Payment Status

```sql
SELECT
    payment_status as "Payment Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 13, "col": 6, "size_x": 6, "size_y": 6 }
```

#### Question: Orders by Channel

```sql
SELECT
    COALESCE(c.channel_name, 'Unknown') as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue"
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Section 3 — Cảnh báo

### ▸ Đơn bất thường — cần mở Sapo xác minh từng dòng

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Flagged Orders

```sql
SELECT
    o.order_code as "Order Code",
    o.status as "Status",
    COALESCE(ch.channel_name, 'Unknown') as "Channel",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.total_collected as "Collected",
    CASE
        WHEN o.total_collected = 0 AND o.discount_amount > 0 THEN '100% Discount'
        WHEN o.net_revenue < 0 THEN 'Negative Revenue'
        WHEN o.discount_amount > o.gross_revenue THEN 'Discount > Gross'
        WHEN o.status = 'COMPLETED' AND o.payment_status != 'PAID' THEN 'Completed but Unpaid'
        WHEN o.payment_status = 'REFUNDED' THEN 'Refunded'
    END as "Flag"
FROM fact_orders o
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
  AND (
    (o.total_collected = 0 AND o.discount_amount > 0)
    OR o.net_revenue < 0
    OR o.discount_amount > o.gross_revenue
    OR (o.status = 'COMPLETED' AND o.payment_status != 'PAID')
    OR o.payment_status = 'REFUNDED'
  )
ORDER BY o.discount_amount DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### 📝 Text: Section 4 — Chi tiết

### ▸ Chi tiết đơn hàng — search order code trên Sapo nếu lệch

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Order Detail List

```sql
SELECT
    o.order_id as "order_id",
    o.order_code as "Order Code",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.tax_amount as "Tax",
    o.total_collected as "Collected",
    COALESCE(ch.channel_name, 'Unknown') as "Channel",
    o.payment_status as "Payment",
    o.fulfillment_status as "Fulfillment",
    c.full_name as "Customer",
    c.phone as "Phone",
    bl.branch_location_name as "Store"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
LEFT JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "table.columns": [
      {"name": "order_id", "enabled": false}
    ],
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Tax": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" },
      "[\"name\",\"Order Code\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "dashboard",
          "targetId": 38,
          "parameterMapping": {
            "order_id": {
              "source": { "type": "column", "id": "order_id", "name": "order_id" },
              "target": { "type": "parameter", "id": "order_id" },
              "id": "order_id"
            }
          }
        }
      }
    }
  }
}
```

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Footer — Source & Escalation

Source: `fact_orders` · dbt updates every 10 min via Dagster incremental job · Filter: `status NOT IN ('CANCELLED', 'Voided')` for revenue KPIs · Playbook: [orders_list_reconciliation](../playbooks/orders_list_reconciliation.md) · For help: #data-team

```json metabase-pos
{ "row": 36, "col": 0, "size_x": 18, "size_y": 1 }
```


---


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_* · **Cadence:** rolling-30d · **Scope:** Period filter
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### Tab: By Date


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

#### Filter: Date

```json metabase-filter
{
  "name": "Date",
  "slug": "date",
  "type": "date/single",
  "default": "today"
}
```

#### 📝 Text: Reconciliation Checklist


#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_* · **Cadence:** rolling-30d · **Scope:** Period filter
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

## 🔍 Đối chiếu BI ↔ Sapo — 5 bước

1. **So Total Orders** với Sapo Admin > Đơn hàng cùng ngày (bao gồm cả CANCELLED).
2. **So Net Revenue** và **Total Collected** với cùng bộ lọc.
3. **Kiểm tra DoD arrow** — đỏ/bất thường → cần điều tra ngay.
4. **Quét Flagged Orders** — bất kỳ dòng nào cũng cần xác minh Sapo.
5. **Lệch > 1 đơn?** Mở Order Detail List, search order code trên Sapo → báo Data Team nếu là ingestion gap.

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 15, "size_y": 2 }
```

#### Question: Data Freshness

Tuổi của dữ liệu — xanh nếu < 120 phút, cam 120-360 phút, đỏ > 360 phút. Nếu > 120 phút, dừng reconciliation và kiểm tra Dagster trước.

```sql
SELECT
    CAST(date_diff('minute', MAX(updated_at), now()) AS INTEGER) AS "Phút kể từ lần cập nhật cuối"
FROM fact_orders
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.field": "Phút kể từ lần cập nhật cuối"
  }
}
```

```json metabase-pos
{ "row": 0, "col": 15, "size_x": 3, "size_y": 2 }
```

---

#### 📝 Text: Section 1 — Tổng quan

### ▸ Tổng quan đơn hàng — số cần đối soát với Sapo

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Total Orders

```sql
WITH current_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}}
),
previous_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}} - INTERVAL '1 day'
)
SELECT c.val as "Total Orders", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 4, "col": 0, "size_x": 6, "size_y": 4 }
```

#### Question: Net Revenue

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}}
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(net_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}} - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Net Revenue", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Net Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 6, "size_x": 4, "size_y": 4 }
```

#### Question: Total Collected

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}}
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(total_collected), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}} - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Total Collected", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Total Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 10, "size_x": 4, "size_y": 4 }
```

#### Question: Gross Revenue

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}}
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(gross_revenue), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}} - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Gross Revenue", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Gross Revenue": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 4, "col": 14, "size_x": 4, "size_y": 4 }
```

#### Question: Total Discount

```sql
WITH current_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}}
      AND status NOT IN ('CANCELLED', 'Voided')
),
previous_period AS (
    SELECT COALESCE(SUM(discount_amount), 0) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}} - INTERVAL '1 day'
      AND status NOT IN ('CANCELLED', 'Voided')
)
SELECT c.val as "Total Discount", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ],
    "column_settings": {
      "Total Discount": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 6, "size_y": 4 }
```

#### Question: Cancelled Orders

```sql
WITH current_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}}
      AND status = 'CANCELLED'
),
previous_period AS (
    SELECT COUNT(DISTINCT order_id) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}} - INTERVAL '1 day'
      AND status = 'CANCELLED'
)
SELECT c.val as "Cancelled", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 6, "size_x": 6, "size_y": 4 }
```

#### Question: Returns

```sql
WITH current_period AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}}
),
previous_period AS (
    SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as val
    FROM fact_orders
    WHERE date(order_timestamp) = {{date}} - INTERVAL '1 day'
)
SELECT c.val as "Returns", p.val as "Previous"
FROM current_period c, previous_period p
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_day",
        "type": "anotherColumn",
        "column": "Previous",
        "label": "vs Hom truoc"
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 8, "col": 12, "size_x": 6, "size_y": 4 }
```

---

#### 📝 Text: Section 2 — Phân bổ

### ▸ Phân bổ theo chiều — phát hiện lệch trạng thái, thanh toán, kênh

```json metabase-pos
{ "row": 12, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Status

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 13, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Orders by Payment Status

```sql
SELECT
    payment_status as "Payment Status",
    COUNT(DISTINCT order_id) as "Orders"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.show_legend": true,
    "pie.show_total": true,
    "pie.percent_visibility": "inside"
  }
}
```

```json metabase-pos
{ "row": 13, "col": 6, "size_x": 6, "size_y": 6 }
```

#### Question: Orders by Channel

```sql
SELECT
    COALESCE(c.channel_name, 'Unknown') as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue"
FROM fact_orders o
LEFT JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = {{date}}
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 3 DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["Channel"],
    "graph.metrics": ["Revenue"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "Revenue (VND)",
    "column_settings": {
      "Revenue": { "number_style": "currency", "currency": "VND", "compact": true }
    }
  }
}
```

```json metabase-pos
{ "row": 13, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Section 3 — Cảnh báo

### ▸ Đơn bất thường — cần mở Sapo xác minh từng dòng

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Flagged Orders

```sql
SELECT
    o.order_code as "Order Code",
    o.status as "Status",
    COALESCE(ch.channel_name, 'Unknown') as "Channel",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.total_collected as "Collected",
    CASE
        WHEN o.total_collected = 0 AND o.discount_amount > 0 THEN '100% Discount'
        WHEN o.net_revenue < 0 THEN 'Negative Revenue'
        WHEN o.discount_amount > o.gross_revenue THEN 'Discount > Gross'
        WHEN o.status = 'COMPLETED' AND o.payment_status != 'PAID' THEN 'Completed but Unpaid'
        WHEN o.payment_status = 'REFUNDED' THEN 'Refunded'
    END as "Flag"
FROM fact_orders o
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = {{date}}
  AND (
    (o.total_collected = 0 AND o.discount_amount > 0)
    OR o.net_revenue < 0
    OR o.discount_amount > o.gross_revenue
    OR (o.status = 'COMPLETED' AND o.payment_status != 'PAID')
    OR o.payment_status = 'REFUNDED'
  )
ORDER BY o.discount_amount DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 20, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### 📝 Text: Section 4 — Chi tiết

### ▸ Chi tiết đơn hàng — search order code trên Sapo nếu lệch

```json metabase-pos
{ "row": 25, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Order Detail List

```sql
SELECT
    o.order_id as "order_id",
    o.order_code as "Order Code",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.tax_amount as "Tax",
    o.total_collected as "Collected",
    COALESCE(ch.channel_name, 'Unknown') as "Channel",
    o.payment_status as "Payment",
    o.fulfillment_status as "Fulfillment",
    c.full_name as "Customer",
    c.phone as "Phone",
    bl.branch_location_name as "Store"
FROM fact_orders o
LEFT JOIN dim_customers c ON o.customer_key = c.customer_key
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
LEFT JOIN dim_branch_location bl ON o.branch_location_key = bl.branch_location_key
WHERE date(o.order_timestamp) = {{date}}
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "table.columns": [
      {"name": "order_id", "enabled": false}
    ],
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Tax": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" },
      "[\"name\",\"Order Code\"]": {
        "click_behavior": {
          "type": "link",
          "linkType": "dashboard",
          "targetId": 38,
          "parameterMapping": {
            "order_id": {
              "source": { "type": "column", "id": "order_id", "name": "order_id" },
              "target": { "type": "parameter", "id": "order_id" },
              "id": "order_id"
            }
          }
        }
      }
    }
  }
}
```

```json metabase-pos
{ "row": 26, "col": 0, "size_x": 18, "size_y": 10 }
```

---

#### 📝 Text: Footer — Source & Escalation

Source: `fact_orders` · dbt updates every 10 min via Dagster incremental job · Filter: `status NOT IN ('CANCELLED', 'Voided')` for revenue KPIs · Playbook: [orders_list_reconciliation](../playbooks/orders_list_reconciliation.md) · For help: #data-team

```json metabase-pos
{ "row": 36, "col": 0, "size_x": 18, "size_y": 1 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_orders + dim_* · **Cadence:** rolling-30d · **Scope:** Period filter
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


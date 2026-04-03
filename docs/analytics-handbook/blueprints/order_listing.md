# Blueprint: Order Listing

**Design Spec**: [Order Listing](../designs/order_listing.md)
**Playbook**: [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

> **Target Collection:** `Operations` > `Daily Monitoring`
> **Role:** Sales Ops, Store Manager, Data Team
> **Archetype:** Operational Cockpit

## Collection: Operations > Daily Monitoring

Dashboard doi soat don hang voi visual da dang: KPI co DoD trend, donut breakdowns, bar chart kenh ban.
Muc tieu: xac minh tinh dung dan va day du cua du lieu so voi Sapo.

---

### Dashboard: Order Listing

**Description**: Cong cu doi soat don hang — KPI voi xu huong DoD, phan bo trang thai/thanh toan (donut), kenh ban (bar), canh bao bat thuong, va chi tiet tung don. 3 tabs: Today, Yesterday, By Date.

---

### Tab: Today

#### 📝 Text: Review tổng quan đơn hàng — đối soát số liệu với Sapo

## Review tổng quan đơn hàng — đối soát số liệu với Sapo

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
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
{ "row": 0, "col": 0, "size_x": 6, "size_y": 4 }
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
{ "row": 0, "col": 6, "size_x": 4, "size_y": 4 }
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
{ "row": 0, "col": 10, "size_x": 4, "size_y": 4 }
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
{ "row": 0, "col": 14, "size_x": 4, "size_y": 4 }
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
{ "row": 4, "col": 0, "size_x": 6, "size_y": 4 }
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
{ "row": 4, "col": 6, "size_x": 6, "size_y": 4 }
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
{ "row": 4, "col": 12, "size_x": 6, "size_y": 4 }
```

---

#### 📝 Text: Kiểm tra phân bổ trạng thái, thanh toán, và kênh bán

## Kiểm tra phân bổ trạng thái, thanh toán, và kênh bán

```json metabase-pos
{ "row": 8, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Orders by Status

Kiem tra phan bo trang thai — phat hien neu qua nhieu don OPEN/CANCELLED.

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
{ "row": 8, "col": 0, "size_x": 6, "size_y": 6 }
```

#### Question: Orders by Payment Status

Doi soat thanh toan — phat hien don chua thanh toan hoac hoan tien.

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
{ "row": 8, "col": 6, "size_x": 6, "size_y": 6 }
```

#### Question: Orders by Channel

Kiem tra tat ca kenh deu co du lieu — phat hien kenh bi mat don.

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
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

---

#### 📝 Text: Điều tra đơn bất thường — anomaly và data gap

## Điều tra đơn bất thường — anomaly và data gap

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Flagged Orders

Don hang bat thuong can kiem tra: 100% discount, revenue am, discount > revenue.

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
{ "row": 14, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### 📝 Text: Đối soát chi tiết đơn hàng — đối chiếu từng dòng với Sapo

## Đối soát chi tiết đơn hàng — đối chiếu từng dòng với Sapo

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 1 }
```

#### Question: Order Detail List

Danh sach day du de doi soat tung don voi Sapo.

**Domain Reference**: [Order Detail List](../domains/sales.md#17-order-detail-list)

```sql
SELECT
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
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Tax": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 10 }
```

---

### Tab: Yesterday

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
{ "row": 0, "col": 0, "size_x": 6, "size_y": 4 }
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
{ "row": 0, "col": 6, "size_x": 4, "size_y": 4 }
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
{ "row": 0, "col": 10, "size_x": 4, "size_y": 4 }
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
{ "row": 0, "col": 14, "size_x": 4, "size_y": 4 }
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
{ "row": 4, "col": 0, "size_x": 6, "size_y": 4 }
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
{ "row": 4, "col": 6, "size_x": 6, "size_y": 4 }
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
{ "row": 4, "col": 12, "size_x": 6, "size_y": 4 }
```

---

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
{ "row": 8, "col": 0, "size_x": 6, "size_y": 6 }
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
{ "row": 8, "col": 6, "size_x": 6, "size_y": 6 }
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
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

---

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
{ "row": 14, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### Question: Order Detail List

```sql
SELECT
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
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Tax": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 10 }
```

---

### Tab: By Date

#### Filter: Date

```json metabase-filter
{
  "name": "Date",
  "slug": "date",
  "type": "date/single",
  "default": "today"
}
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
{ "row": 0, "col": 0, "size_x": 6, "size_y": 4 }
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
{ "row": 0, "col": 6, "size_x": 4, "size_y": 4 }
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
{ "row": 0, "col": 10, "size_x": 4, "size_y": 4 }
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
{ "row": 0, "col": 14, "size_x": 4, "size_y": 4 }
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
{ "row": 4, "col": 0, "size_x": 6, "size_y": 4 }
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
{ "row": 4, "col": 6, "size_x": 6, "size_y": 4 }
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
{ "row": 4, "col": 12, "size_x": 6, "size_y": 4 }
```

---

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
{ "row": 8, "col": 0, "size_x": 6, "size_y": 6 }
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
{ "row": 8, "col": 6, "size_x": 6, "size_y": 6 }
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
{ "row": 8, "col": 12, "size_x": 6, "size_y": 6 }
```

---

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
{ "row": 14, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### Question: Order Detail List

```sql
SELECT
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
    "column_settings": {
      "Gross": { "number_style": "currency", "currency": "VND" },
      "Discount": { "number_style": "currency", "currency": "VND" },
      "Net Revenue": { "number_style": "currency", "currency": "VND" },
      "Tax": { "number_style": "currency", "currency": "VND" },
      "Collected": { "number_style": "currency", "currency": "VND" }
    }
  }
}
```

```json metabase-pos
{ "row": 19, "col": 0, "size_x": 18, "size_y": 10 }
```

#### 📝 Text: Source & Freshness

Source: fact_orders · Updated daily · All channels included

```json metabase-pos
{ "row": 29, "col": 0, "size_x": 18, "size_y": 1 }
```

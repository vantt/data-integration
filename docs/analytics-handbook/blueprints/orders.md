# 📘 Blueprint: Orders

**Playbook**: [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

> **Target Collection:** `Operations` > `Daily Monitoring`
> **Role:** Sales Ops, Store Manager, Kế toán
> **Archetype:** Operational Cockpit

## 📂 Collection: Operations > Daily Monitoring

Dashboard đối soát đơn hàng. Ba tab: Today (real-time), Yesterday (finalized), By Date (tùy chọn).
Mục tiêu: xác minh tính đúng đắn và đầy đủ của dữ liệu so với Sapo.

---

### 🖥️ Dashboard: Orders

**Description**: Công cụ đối soát đơn hàng — so khớp tổng số, phát hiện bất thường, kiểm tra theo kênh/thanh toán/trạng thái. 3 tabs: Today, Yesterday, By Date.

---

### 📑 Tab: Today

#### ❓ Question: Total Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Net Revenue

```sql
SELECT COALESCE(SUM(net_revenue), 0) as "Net Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Net Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 3, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Total Collected

Số tiền thực thu (gồm thuế) — dùng để đối soát với kế toán/ngân hàng.

```sql
SELECT COALESCE(SUM(total_collected), 0) as "Total Collected"
FROM fact_orders
WHERE date(order_timestamp) = current_date
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total Collected": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 6, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Total Discount

```sql
SELECT COALESCE(SUM(discount_amount), 0) as "Total Discount"
FROM fact_orders
WHERE date(order_timestamp) = current_date
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total Discount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Cancelled Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Cancelled"
FROM fact_orders
WHERE date(order_timestamp) = current_date
  AND status = 'CANCELLED'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Returns

```sql
SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as "Returns"
FROM fact_orders
WHERE date(order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Orders by Status

Kiểm tra phân bố trạng thái — phát hiện nếu quá nhiều đơn OPEN/CANCELLED.

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(total_collected), 0) as "Amount"
FROM fact_orders
WHERE date(order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Amount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 5 }
```

#### ❓ Question: Orders by Payment Status

Đối soát thanh toán — phát hiện đơn chưa thanh toán hoặc hoàn tiền.

```sql
SELECT
    payment_status as "Payment Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(total_collected), 0) as "Amount"
FROM fact_orders
WHERE date(order_timestamp) = current_date
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Amount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 5 }
```

#### ❓ Question: Orders by Channel

Kiểm tra tất cả kênh đều có dữ liệu — phát hiện kênh bị mất đơn.

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 5 }
```

---

#### ❓ Question: Flagged Orders

Đơn hàng bất thường cần kiểm tra: 100% discount, revenue = 0, discount > revenue.

```sql
SELECT
    o.order_id as "Order ID",
    o.status as "Status",
    ch.channel_name as "Channel",
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### ❓ Question: Order Detail List

Danh sách đầy đủ để đối soát từng đơn với Sapo.

**Domain Reference**: [Order Detail List](../domains/sales.md#17-order-detail-list)

```sql
SELECT
    o.order_id as "Order ID",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.payment_status as "Payment",
    o.fulfillment_status as "Fulfillment",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.tax_amount as "Tax",
    o.total_collected as "Collected",
    ch.channel_name as "Channel",
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
{ "row": 13, "col": 0, "size_x": 18, "size_y": 12 }
```

---

### 📑 Tab: Yesterday

#### ❓ Question: Total Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Net Revenue

```sql
SELECT COALESCE(SUM(net_revenue), 0) as "Net Revenue"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Net Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 3, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Total Collected

```sql
SELECT COALESCE(SUM(total_collected), 0) as "Total Collected"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total Collected": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 6, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Total Discount

```sql
SELECT COALESCE(SUM(discount_amount), 0) as "Total Discount"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total Discount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Cancelled Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Cancelled"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
  AND status = 'CANCELLED'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Returns

```sql
SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as "Returns"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Orders by Status

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(total_collected), 0) as "Amount"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Amount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 5 }
```

#### ❓ Question: Orders by Payment Status

```sql
SELECT
    payment_status as "Payment Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(total_collected), 0) as "Amount"
FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Amount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 5 }
```

#### ❓ Question: Orders by Channel

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 5 }
```

---

#### ❓ Question: Flagged Orders

```sql
SELECT
    o.order_id as "Order ID",
    o.status as "Status",
    ch.channel_name as "Channel",
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### ❓ Question: Order Detail List

```sql
SELECT
    o.order_id as "Order ID",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.payment_status as "Payment",
    o.fulfillment_status as "Fulfillment",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.tax_amount as "Tax",
    o.total_collected as "Collected",
    ch.channel_name as "Channel",
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
{ "row": 13, "col": 0, "size_x": 18, "size_y": 12 }
```

---

### 📑 Tab: By Date

#### Filter: Date

```json metabase-filter
{
  "name": "Date",
  "slug": "date",
  "type": "date/single",
  "default": "today"
}
```

#### ❓ Question: Total Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Total Orders"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Net Revenue

```sql
SELECT COALESCE(SUM(net_revenue), 0) as "Net Revenue"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Net Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 3, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Total Collected

```sql
SELECT COALESCE(SUM(total_collected), 0) as "Total Collected"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total Collected": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 6, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Total Discount

```sql
SELECT COALESCE(SUM(discount_amount), 0) as "Total Discount"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
  AND status NOT IN ('CANCELLED', 'Voided')
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": { "Total Discount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 0, "col": 9, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Cancelled Orders

```sql
SELECT COUNT(DISTINCT order_id) as "Cancelled"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
  AND status = 'CANCELLED'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 3, "size_y": 3 }
```

#### ❓ Question: Returns

```sql
SELECT COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END) as "Returns"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Orders by Status

```sql
SELECT
    status as "Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(total_collected), 0) as "Amount"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Amount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 6, "size_y": 5 }
```

#### ❓ Question: Orders by Payment Status

```sql
SELECT
    payment_status as "Payment Status",
    COUNT(DISTINCT order_id) as "Orders",
    COALESCE(SUM(total_collected), 0) as "Amount"
FROM fact_orders
WHERE date(order_timestamp) = {{date}}
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Amount": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 6, "size_x": 6, "size_y": 5 }
```

#### ❓ Question: Orders by Channel

```sql
SELECT
    c.channel_name as "Channel",
    COUNT(DISTINCT o.order_id) as "Orders",
    COALESCE(SUM(o.net_revenue), 0) as "Revenue"
FROM fact_orders o
JOIN dim_channels c ON o.channel_key = c.channel_key
WHERE date(o.order_timestamp) = {{date}}
  AND o.status NOT IN ('CANCELLED', 'Voided')
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "visualization_settings": {
    "column_settings": { "Revenue": { "number_style": "currency", "currency": "VND" } }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 6, "size_y": 5 }
```

---

#### ❓ Question: Flagged Orders

```sql
SELECT
    o.order_id as "Order ID",
    o.status as "Status",
    ch.channel_name as "Channel",
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
{ "row": 8, "col": 0, "size_x": 18, "size_y": 5 }
```

---

#### ❓ Question: Order Detail List

```sql
SELECT
    o.order_id as "Order ID",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.payment_status as "Payment",
    o.fulfillment_status as "Fulfillment",
    o.gross_revenue as "Gross",
    o.discount_amount as "Discount",
    o.net_revenue as "Net Revenue",
    o.tax_amount as "Tax",
    o.total_collected as "Collected",
    ch.channel_name as "Channel",
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
{ "row": 13, "col": 0, "size_x": 18, "size_y": 12 }
```

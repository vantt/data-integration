# 📘 Blueprint: Orders

**Playbook**: [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

> **Target Collection:** `Operations` > `Daily Monitoring`
> **Role:** Sales Ops, Store Manager
> **Archetype:** Operational Cockpit

## 📂 Collection: Operations > Daily Monitoring

Order-level listing for reconciliation with Sapo. Three tabs: Today, Yesterday, and By Date (custom date picker).

---

### 🖥️ Dashboard: Orders

**Description**: Order listing with 3 tabs — Today (real-time), Yesterday (finalized), By Date (custom). Cross-check with Sapo admin to verify data completeness.

---

### 📑 Tab: Today

#### ❓ Question: Date Label

```sql
SELECT strftime(current_date, '%Y-%m-%d') as "Date"
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Total Orders Count

```sql
SELECT count(distinct o.order_id) as "Total Orders"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 6, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Total Revenue

```sql
SELECT coalesce(sum(o.net_revenue), 0) as "Total Revenue"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Order Detail List

**Domain Reference**: [Order Detail List](../domains/sales.md#17-order-detail-list)

```sql
SELECT
    o.order_id as "Order ID",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.payment_status as "Payment Status",
    o.fulfillment_status as "Fulfillment",
    o.net_revenue as "Revenue",
    o.discount_amount as "Discount",
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
  "table.column_formatting": [
    { "columns": ["Revenue", "Discount"], "type": "currency", "currency": "VND" }
  ]
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 16 }
```

---

### 📑 Tab: Yesterday

#### ❓ Question: Date Label

```sql
SELECT strftime(current_date - INTERVAL '1 day', '%Y-%m-%d') as "Date"
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Total Orders Count

```sql
SELECT count(distinct o.order_id) as "Total Orders"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 6, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Total Revenue

```sql
SELECT coalesce(sum(o.net_revenue), 0) as "Total Revenue"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Order Detail List

```sql
SELECT
    o.order_id as "Order ID",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.payment_status as "Payment Status",
    o.fulfillment_status as "Fulfillment",
    o.net_revenue as "Revenue",
    o.discount_amount as "Discount",
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
  "table.column_formatting": [
    { "columns": ["Revenue", "Discount"], "type": "currency", "currency": "VND" }
  ]
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 16 }
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

#### ❓ Question: Date Label

```sql
SELECT strftime({{date}}, '%Y-%m-%d') as "Date"
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Total Orders Count

```sql
SELECT count(distinct o.order_id) as "Total Orders"
FROM fact_orders o
WHERE date(o.order_timestamp) = {{date}}
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 6, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Total Revenue

```sql
SELECT coalesce(sum(o.net_revenue), 0) as "Total Revenue"
FROM fact_orders o
WHERE date(o.order_timestamp) = {{date}}
```

```json metabase-viz
{ "display": "scalar" }
```

```json metabase-pos
{ "row": 0, "col": 12, "size_x": 6, "size_y": 2 }
```

#### ❓ Question: Order Detail List

```sql
SELECT
    o.order_id as "Order ID",
    strftime(o.order_timestamp, '%H:%M') as "Time",
    o.status as "Status",
    o.payment_status as "Payment Status",
    o.fulfillment_status as "Fulfillment",
    o.net_revenue as "Revenue",
    o.discount_amount as "Discount",
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
  "table.column_formatting": [
    { "columns": ["Revenue", "Discount"], "type": "currency", "currency": "VND" }
  ]
}
```

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 16 }
```

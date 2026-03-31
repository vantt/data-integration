# Orders by Date Blueprint

**Based on**: [Today's Orders List](orders_today.md)

Order-level listing for any selected date — same layout as Today's Orders but with a date picker filter.

## 📂 Collection: Operations > Daily Monitoring

### Model: Orders by Date (Detail)

All orders with key reconciliation fields, filterable by date.

```sql
SELECT * FROM fact_orders
```

---

### Dashboard: Orders by Date

**Description**: Order listing for any date. Use the date filter to pick the day you want to review. Defaults to today.

#### Filter: Date

```json metabase-filter
{
  "name": "Date",
  "slug": "date",
  "type": "date/single",
  "default": "today"
}
```

#### Question: Date Label

```sql
SELECT strftime({{date}}, '%Y-%m-%d') as "Date"
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 6,
  "size_y": 2
}
```

#### Question: Total Orders Count

```sql
SELECT count(distinct o.order_id) as "Total Orders"
FROM fact_orders o
WHERE date(o.order_timestamp) = {{date}}
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 6,
  "size_x": 6,
  "size_y": 2
}
```

#### Question: Total Revenue

```sql
SELECT coalesce(sum(o.net_revenue), 0) as "Total Revenue"
FROM fact_orders o
WHERE date(o.order_timestamp) = {{date}}
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 12,
  "size_x": 6,
  "size_y": 2
}
```

#### Question: Order Detail List

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
WHERE date(o.order_timestamp) = {{date}}
ORDER BY o.order_timestamp DESC
```

```json metabase-viz
{
  "display": "table",
  "table.pivot": false,
  "table.column_formatting": [
    {
      "columns": ["Revenue", "Discount"],
      "type": "currency",
      "currency": "VND"
    }
  ]
}
```

```json metabase-pos
{
  "row": 2,
  "col": 0,
  "size_x": 18,
  "size_y": 16
}
```

# Yesterday's Orders List Blueprint

**Playbook**: [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

Finalized order-level listing of yesterday's orders for reconciliation with the Sapo sales system.

## 📂 Collection: Operations > Daily Monitoring

### Model: Yesterday's Orders (Detail)

All orders from the previous date — finalized, no further changes expected.

```sql
SELECT * FROM fact_orders
WHERE date(order_timestamp) = current_date - INTERVAL '1 day'
```

---

### Dashboard: Yesterday's Orders

**Description**: Finalized order listing for yesterday. Cross-check with Sapo admin to verify data completeness.

#### Question: Date Label

```sql
SELECT strftime(current_date - INTERVAL '1 day', '%Y-%m-%d') as "Date"
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
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
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

#### Question: Total GMV

```sql
SELECT coalesce(sum(o.gmv), 0) as "Total GMV"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date - INTERVAL '1 day'
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
    o.gmv as "GMV",
    o.total_discount_amount as "Discount",
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
    {
      "columns": ["GMV", "Discount"],
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

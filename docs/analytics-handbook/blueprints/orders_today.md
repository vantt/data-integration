# Today's Orders List Blueprint

**Playbook**: [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

Order-level listing of today's orders for reconciliation with the Sapo sales system.

## Collection: Daily Operations

### Model: Today's Orders (Detail)

All orders from the current date with key reconciliation fields.

```sql
SELECT * FROM fact_orders
WHERE date(order_timestamp) = current_date
```

---

### Dashboard: Today's Orders

**Description**: Real-time order listing for today. Cross-check with Sapo admin to verify data completeness.

#### Question: Date Label

```sql
SELECT to_char(current_date, 'YYYY-MM-DD') as "Date"
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
  "size_x": 4,
  "size_y": 2
}
```

#### Question: Total Orders Count

```sql
SELECT count(distinct o.order_id) as "Total Orders"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 4,
  "size_x": 4,
  "size_y": 2
}
```

#### Question: Total GMV

```sql
SELECT coalesce(sum(o.gmv), 0) as "Total GMV"
FROM fact_orders o
WHERE date(o.order_timestamp) = current_date
```

```json metabase-viz
{
  "display": "scalar"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 8,
  "size_x": 4,
  "size_y": 2
}
```

#### Question: Order Detail List

**Domain Reference**: [Order Detail List](../domains/sales.md#17-order-detail-list)

```sql
SELECT
    stg.order_code as "Order Code",
    to_char(o.order_timestamp, 'HH24:MI') as "Time",
    o.status as "Status",
    o.payment_status as "Payment Status",
    o.fulfillment_status as "Fulfillment",
    o.gmv as "GMV",
    o.total_discount_amount as "Discount",
    ch.channel_name as "Channel",
    stg.customer_name as "Customer",
    stg.customer_phone as "Phone",
    stg.payment_method_name as "Payment Method",
    stg.location_name as "Store"
FROM fact_orders o
LEFT JOIN stg_sapo_orders stg ON cast(o.order_id as string) = stg.order_id
LEFT JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE date(o.order_timestamp) = current_date
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

# Logistics Domain

> **Owner:** Operations / Warehouse
> **Update Frequency:** Real-time / Hourly

## Context: Order Processing & Fulfillment

> **Description:** Order processing efficiency — from order creation to first shipment.
> **dbt Source:** `fact_orders` (via `std_orders` + `std_fulfillments`)

### 1. Fulfillment Rate

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Percentage of eligible orders that have been fulfilled (shipped).
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN fulfillment_status = 'fulfilled' THEN 1 END) * 100.0
  / NULLIF(COUNT(*), 0)
  -- WHERE status NOT IN ('DRAFT', 'CANCELLED')
  ```

### 2. Order Cycle Time

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Average time from order creation to first shipment.
- **Logic (SQL):**
  ```sql
  AVG(date_diff('hour', order_timestamp, first_shipped_at)) as avg_hours_to_first_ship
  -- Only for orders WHERE first_shipped_at IS NOT NULL
  ```
- **Note:** `time_to_complete_hours` measures created-to-completed (different metric). Use `first_shipped_at` for shipping speed.

### 3. Same-Day Ship Rate

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Percentage of orders shipped on the same calendar day they were created.
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN CAST(first_shipped_at AS DATE) = CAST(order_timestamp AS DATE) THEN 1 END) * 100.0
  / NULLIF(COUNT(CASE WHEN first_shipped_at IS NOT NULL THEN 1 END), 0)
  ```

### 4. Time to Complete

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Average time from order creation to order completion (status = COMPLETED).
- **Logic (SQL):**
  ```sql
  AVG(time_to_complete_hours) as avg_completion_hours
  -- WHERE status = 'COMPLETED'
  ```

## Context: Shipping & Delivery (Planned)

> **Description:** Carrier performance and customer receipt.
> **Status:** **Planned** — requires `fact_shipments`, `dim_carriers`. No data sources available yet.

### 5. Avg Delivery Time

> **dbt Model:** `fact_shipments` — **Planned** (model does not exist)

- **Business Definition:** Average time from Shipment to Delivery.
- **Logic (SQL):**
  ```sql
  AVG(Delivered_Timestamp - Shipped_Timestamp)
  ```

### 6. On-Time Delivery Rate

> **dbt Model:** `fact_shipments` — **Planned** (model does not exist)

- **Business Definition:** Percentage of orders delivered by the promised date.
- **Logic (SQL):**
  ```sql
  Count(Delivered_Start <= Promised_Date) / Total_Delivered
  ```

### 7. Return Rate

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available** (partial)

- **Business Definition:** Percentage of shipped orders that are returned.
- **Logic (SQL):**
  ```sql
  -- Requires tracking return status in fulfillment_status or a separate returns model.
  -- Currently estimable via status transitions but not precise.
  ```
- **Note:** Accurate return tracking requires dedicated returns data source. Currently not reliably computable from `fact_orders` alone.

## Context: Staff & Operations

### 8. Staff Performance

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) JOIN [`dim_staff`](../../../transformation/models/marts/core/dim_staff.sql) — **Available**

- **Business Definition:** Orders processed and processing speed by staff member.
- **Logic (SQL):**
  ```sql
  SELECT
      ds.staff_name,
      COUNT(DISTINCT fo.order_id) as total_orders,
      AVG(fo.time_to_complete_hours) as avg_processing_hours
  FROM fact_orders fo
  JOIN dim_staff ds ON fo.seller_staff_key = ds.staff_key
  WHERE fo.status NOT IN ('DRAFT', 'CANCELLED')
  GROUP BY 1
  ```

### 9. Order Status Funnel

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Count of orders in each stage of the processing pipeline.
- **Logic (Ordering):**
  ```sql
  SELECT
      status,
      COUNT(*) as order_count
  FROM fact_orders
  WHERE status != 'DRAFT'
  GROUP BY status
  ORDER BY
      CASE status
          WHEN 'OPEN' THEN 1
          WHEN 'COMPLETED' THEN 2
          WHEN 'ARCHIVED' THEN 3
          WHEN 'CANCELLED' THEN 4
      END
  ```

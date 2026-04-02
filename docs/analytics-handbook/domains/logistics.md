# Logistics Domain

> **Owner:** Operations / Warehouse
> **Update Frequency:** Real-time / Hourly

## Context: Fulfillment

> **Description:** Order processing efficiency.
> **dbt Source:** `fulfillments`, `orders`

### 1. Fulfillment Rate

> **dbt Model:** `fact_orders` (Planned)

- **Business Definition:** Percentage of orders shipped vs total orders.
- **Logic (SQL):**
  ```sql
  Shipped_Count / Total_Orders * 100
  ```

### 2. Order Cycle Time

> **dbt Model:** `fact_fulfillments` (Planned)

- **Business Definition:** Time taken from Order Creation to Shipment.
- **Logic (SQL):**
  ```sql
  Shipped_Timestamp - Created_Timestamp
  ```
- **Detailed Logic (SQL):**
  ```sql
  AVG(EXTRACT(EPOCH FROM (f.shipped_on - f.created_on))/3600) as avg_processing_hours
  ```

### 3. Same-Day Ship Rate

> **dbt Model:** `fact_fulfillments` (Planned)

- **Business Definition:** Percentage of orders shipped on the same day they were placed (before cutoff).
- **Logic (SQL):**
  ```sql
  Count(Same_Day_Shipped) / Total_Orders
  ```
- **Detailed Logic (SQL):**
  ```sql
  COUNT(CASE WHEN f.shipped_on <= f.created_on + INTERVAL '24 hours' THEN 1 END) * 100.0 /
  COUNT(*) as same_day_fulfillment_rate
  ```

## Context: Shipping & Delivery

> **Description:** Carrier performance and customer receipt.
> **dbt Source:** `shipments`

### 4. Avg Delivery Time

> **dbt Model:** `fact_shipments` (Planned)

- **Business Definition:** Average time from Shipment to Delivery.
- **Logic (SQL):**
  ```sql
  AVG(Delivered_Timestamp - Shipped_Timestamp)
  ```

### 5. On-Time Delivery Rate

> **dbt Model:** `fact_shipments` (Planned)

- **Business Definition:** Percentage of orders delivered by the promised date.
- **Logic (SQL):**
  ```sql
  Count(Delivered_Start <= Promised_Date) / Total_Delivered
  ```

### 6. Return Rate

> **dbt Model:** [fact_orders](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Percentage of shipped orders that are returned.
- **Logic (SQL):**
  ```sql
  Returns / Shipped_Orders
  ```

## Context: Staff & Operations

### 7. Staff Performance

> **dbt Model:** [dim_staff](../../../transformation/models/marts/core/dim_staff.sql)

- **Business Definition:** Orders processed and revenue handled by staff member.
- **Logic (SQL):**
  ```sql
  SELECT
      a.account_name,
      COUNT(DISTINCT o.order_id) as total_orders,
      SUM(o.total) as total_revenue
  FROM orders o JOIN accounts a USING (account_id)
  GROUP BY 1
  ```

### 8. Order Status Funnel

> **dbt Model:** [fact_orders](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Count of orders in each stage of pipeline.
- **Logic (Ordering):**
  ```sql
  ORDER BY
      CASE status
          WHEN 'draft' THEN 1
          WHEN 'pending' THEN 2
          WHEN 'confirmed' THEN 3
          WHEN 'processing' THEN 4
          WHEN 'completed' THEN 5
          WHEN 'cancelled' THEN 6
      END
  ```

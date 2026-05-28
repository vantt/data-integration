# Logistics Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** Operations / Warehouse
> **Update Frequency:** Real-time / Hourly

## Context: Order Processing & Fulfillment

> **Description:** Order processing efficiency — from order creation to first shipment.
> **dbt Source:** `fact_orders` (via `std_orders` + `std_fulfillments`)

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Order Processing & Fulfillment | Are orders processed and handed to fulfillment at the expected speed? | 1. Fulfillment Rate, 2. Order Cycle Time, 3. Same-Day Ship Rate, 4. Time to Complete | `fact_orders` (via `std_orders` + `std_fulfillments`) | None documented |

### Analytical Questions

#### Q1. Order Processing & Fulfillment Readiness

- **Question:** Are orders processed and handed to fulfillment at the expected speed?
- **Definition:** This question defines whether `Order Processing & Fulfillment` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** operations, time-to-process.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 1. Fulfillment Rate, 2. Order Cycle Time, 3. Same-Day Ship Rate, 4. Time to Complete

### Metrics

#### 1. Fulfillment Rate

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Percentage of eligible orders that have been fulfilled (shipped).
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN fulfillment_status = 'fulfilled' THEN 1 END) * 100.0
  / NULLIF(COUNT(*), 0)
  -- WHERE status NOT IN ('DRAFT', 'CANCELLED')
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2. Order Cycle Time

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Average time from order creation to first shipment.
- **Logic (SQL):**
  ```sql
  AVG(date_diff('hour', order_timestamp, first_shipped_at)) as avg_hours_to_first_ship
  -- Only for orders WHERE first_shipped_at IS NOT NULL
  ```
- **Note:** `time_to_complete_hours` measures created-to-completed (different metric). Use `first_shipped_at` for shipping speed.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** hours/days
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 3. Same-Day Ship Rate

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Percentage of orders shipped on the same calendar day they were created.
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN CAST(first_shipped_at AS DATE) = CAST(order_timestamp AS DATE) THEN 1 END) * 100.0
  / NULLIF(COUNT(CASE WHEN first_shipped_at IS NOT NULL THEN 1 END), 0)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 4. Time to Complete

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available**

- **Business Definition:** Average time from order creation to order completion (status = COMPLETED).
- **Logic (SQL):**
  ```sql
  AVG(time_to_complete_hours) as avg_completion_hours
  -- WHERE status = 'COMPLETED'
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** hours/days
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Shipping & Delivery (Planned)

> **Description:** Carrier performance and customer receipt.
> **Status:** **Planned** — requires `fact_shipments`, `dim_carriers`. No data sources available yet.

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Shipping & Delivery (Planned) | Are shipped orders reaching customers within the promised delivery window? | 5. Avg Delivery Time, 6. On-Time Delivery Rate, 7. Return Rate | See metric-level dbt sources | Source/model implementation required for planned metrics |

### Analytical Questions

#### Q1. Shipping & Delivery (Planned) Readiness

- **Question:** Are shipped orders reaching customers within the promised delivery window?
- **Definition:** This question defines whether `Shipping & Delivery (Planned)` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** logistics, delivery quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 5. Avg Delivery Time, 6. On-Time Delivery Rate, 7. Return Rate

### Metrics

#### 5. Avg Delivery Time

> **dbt Model:** `fact_shipments` — **Planned** (model does not exist)

- **Business Definition:** Average time from Shipment to Delivery.
- **Logic (SQL):**
  ```sql
  AVG(Delivered_Timestamp - Shipped_Timestamp)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** hours/days
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 6. On-Time Delivery Rate

> **dbt Model:** `fact_shipments` — **Planned** (model does not exist)

- **Business Definition:** Percentage of orders delivered by the promised date.
- **Logic (SQL):**
  ```sql
  Count(Delivered_Start <= Promised_Date) / Total_Delivered
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 7. Return Rate

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — **Available** (partial)

- **Business Definition:** Percentage of shipped orders that are returned.
- **Logic (SQL):**
  ```sql
  -- Requires tracking return status in fulfillment_status or a separate returns model.
  -- Currently estimable via status transitions but not precise.
  ```
- **Note:** Accurate return tracking requires dedicated returns data source. Currently not reliably computable from `fact_orders` alone.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Staff & Operations

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Staff & Operations | How productive and consistent is the operations team when processing orders? | 8. Staff Performance, 9. Order Status Funnel | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Staff & Operations Readiness

- **Question:** How productive and consistent is the operations team when processing orders?
- **Definition:** This question defines whether `Staff & Operations` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** operations productivity.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 8. Staff Performance, 9. Order Status Funnel

### Metrics

#### 8. Staff Performance

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

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 9. Order Status Funnel

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

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** count
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

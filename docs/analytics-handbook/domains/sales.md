# Sales Domain

> **Owner:** Sales Team / Data Team
> **Update Frequency:** Real-time / Daily

## Context: Order Performance

> **Description:** Core metrics regarding order volume, revenue, and efficiency.
> **dbt Source:** `fact_orders`
> **Grain:** Per Order

### 1. GMV (Gross Merchandise Value)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Total value of all confirmed orders, before deductions.
- **Logic (Metabase SQL):**
  ```sql
  SUM(gmv)
  ```
- **Metabase Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Gmv` (Aggregation: Sum)

### 2. Net Revenue

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Actual money received (GMV - Returns - Discounts).
- **Logic (Metabase SQL):**
  ```sql
  SUM(gmv - COALESCE(total_discount_amount, 0))
  ```
- **Metabase Mapping:**
  - **Table:** `fact_orders`
  - **Field:** Custom Expression `Sum(Gmv) - Sum(Total Discount Amount)`

### 3. Return Rate & Count

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Count of returned orders.
- **Logic (Metabase SQL):**
- **Logic (Metabase SQL):**
  ```sql
  COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END)
  ```

### 4. Total Orders

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Count of unique confirmed orders.
- **Logic (Metabase SQL):**
  ```sql
  COUNT(DISTINCT order_id)
  ```

### 5. AOV (Average Order Value)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Average revenue generated per order.
- **Logic (Metabase SQL):**
  ```sql
  SUM(gmv) / COUNT(DISTINCT order_id)
  ```

## Available Dashboards

| Dashboard Name                | Audience              | Purpose                                                        | Link                            |
| :---------------------------- | :-------------------- | :------------------------------------------------------------- | :------------------------------ |
| **Sales Executive Dashboard** | Executives / Managers | High-level monthly overview of revenue, channels, and targets. | [Metabase ID 37](/dashboard/37) |
| **Daily Sales Dashboard**     | Ops / Sales Reps      | Real-time monitoring of today's performance and hourly trends. | [Metabase ID 38](/dashboard/38) |

## Context: Operational Trends

> **Description:** Analysis of sales patterns over time (hourly, daily) and by dimensions.

### 6. Hourly Sales Trend

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Sales performance broken down by hour of the day, compared to previous periods.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
      SUM(gmv) as sales
  FROM fact_orders
  GROUP BY 1
  ```

### 7. Hourly Heatmap (Day of Week Analysis)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Sales intensity by Hour of Day and Day of Week.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      EXTRACT(HOUR FROM created_on) as hour_of_day,
      EXTRACT(DOW FROM created_on) as day_of_week, -- 0=Sunday
      COUNT(*) as order_count,
      SUM(gmv) as revenue
  FROM fact_orders
  GROUP BY 1, 2
  ORDER BY 2, 1
  ```

### 8. Sales by Channel

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Revenue breakdown by acquisition channel (e.g., Website, Mobile App, Partner).
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      channel_name,
      SUM(gmv) as revenue
  FROM fact_orders
  JOIN dim_channels USING (channel_key) -- or source_channel column
  GROUP BY 1
  ```

## Context: Product Performance

> **Description:** Best selling products and category performance.

### 9. Top Selling Products

> **dbt Model:** [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql)

- **Business Definition:** Ranking of products by revenue or units sold.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      p.product_name,
      SUM(oli.quantity) as units_sold,
      SUM(oli.revenue) as revenue
  FROM fact_sales oli -- mapped from order_line_items
  JOIN dim_products p USING (product_id)
  GROUP BY 1
  ORDER BY revenue DESC
  ```

## Context: Customer Engagement

### 10. New vs Returning Customers

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Categorization of orders based on whether the customer has purchased before.
- **Logic (Metabase SQL):**
  ```sql
  CASE
    WHEN date(c.first_order_date) = current_date THEN 'New'
    ELSE 'Returning'
  END
  ```

## Context: Payment Operations

### 11. Payment Method Distribution

> **dbt Model:** [`stg_sapo_payments`](../../../transformation/models/staging/stg_sapo_payments.sql)

- **Business Definition:** Transaction count and volume by payment method (Credit Card, COD, etc.).
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      pm.payment_method_name,
      COUNT(*) as transaction_count,
      SUM(p.amount) as total_amount
  FROM stg_sapo_payments p
  JOIN payment_methods pm USING (payment_method_id)
  WHERE p.status = 'completed'
  GROUP BY 1
  ```

### 12. Payment Status

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Tracking of payment success/failure.
- **Logic (Metabase SQL):**
  ```sql
  SELECT payment_status, COUNT(*), SUM(gmv) FROM fact_orders GROUP BY 1
  ```

## Context: Promotions & Discounts

### 13. Discount Impact

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Value of discounts given and percentage of orders discounted.
- **Logic (Metabase SQL):**
  ```sql
  SUM(CASE WHEN total_discount_amount > 0 THEN 1 ELSE 0 END) as discounted_orders,
  SUM(total_discount_amount) as total_discounts,
  AVG(total_discount_amount * 100.0 / NULLIF(gmv, 0)) as avg_discount_pct
  ```

### 14. Promotion Performance

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Revenue and usage by specific promotion campaign.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      pr.promotion_name,
      COUNT(DISTINCT o.order_id) as usage_count,
      SUM(o.gmv) as revenue_with_promo
  FROM fact_orders o
  JOIN promotion_redemptions pr USING (order_id)
  GROUP BY 1
  ```

## Context: Sales Targets

> **Description:** Comparison of actual performance against defined goals.
> **dbt Source:** `fact_targets`

### 15. Target Achievement Rate

> **dbt Model:** [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)

- **Business Definition:** Percentage of target achieved (Actual Revenue / Target Revenue).
- **Logic (Metabase SQL):**
  ```sql
  SUM(actual_revenue) / NULLIF(SUM(target_revenue), 0)
  ```

### 16. Variance to Target

> **dbt Model:** [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)

- **Business Definition:** Absolute difference between Actual and Target.
- **Logic (Metabase SQL):**

  ```sql
  SUM(actual_revenue) - SUM(target_revenue)
  ```

  SUM(actual_revenue) - SUM(target_revenue)

  ```

  ```

> **Implementation Note:**
> Do not attempt to join `fact_orders` and `fact_targets` directly in a Native Query as they have different grains (Order vs Month/Branch).
> **Recommended Approach:** Create a **Metabase Model** (or dbt mart `mart_sales_actual_vs_target`) to pre-aggregate `fact_orders` to the same grain (Month, Branch, Channel) before joining with `fact_targets`.

## Context: Location Analysis

### 15. Sales by Region/Location

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Revenue performance by geographic unit.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      l.region,
      l.location_name,
      SUM(o.gmv) as revenue
  FROM fact_orders o
  JOIN dim_locations l USING (location_id)
  GROUP BY 1, 2
  ```

# Sales Domain

> **Owner:** Sales Team / Data Team
> **Update Frequency:** Real-time / Daily

## Context: Order Performance

> **Description:** Core metrics regarding order volume, revenue, and efficiency.
> **dbt Source:** `fact_orders`
> **Grain:** Per Order

### 1. GMV (Gross Merchandise Value)

- **Business Definition:** Total value of all confirmed orders, before deductions.
- **Logic (SQL):**
  ```sql
  SUM(total) -- or SUM(gmv) depending on specific column availability in fact_orders
  ```
- **Metabase Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Total` (Aggregation: Sum)

### 2. Net Revenue

- **Business Definition:** Actual money received (GMV - Returns - Discounts).
- **Logic (SQL):**
  ```sql
  SUM(total - COALESCE(discount_amount, 0)) -- Adjust based on return logic (e.g. JOIN returns)
  -- Legacy Logic: SUM(total) - SUM(discounts) - SUM(returns)
  ```
- **Metabase Mapping:**
  - **Table:** `fact_orders`
  - **Field:** Custom Expression `Sum(Total) - Sum(Discount Amount)`

### 2.1 Return Rate & Count

- **Business Definition:** Count of returned orders.
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN return_status != 'unreturned' THEN 1 END)
  ```

### 3. Total Orders

- **Business Definition:** Count of unique confirmed orders.
- **Logic (SQL):**
  ```sql
  COUNT(DISTINCT order_id)
  ```

### 4. AOV (Average Order Value)

- **Business Definition:** Average revenue generated per order.
- **Logic (SQL):**
  ```sql
  SUM(total) / COUNT(DISTINCT order_id)
  ```

## Context: Operational Trends

> **Description:** Analysis of sales patterns over time (hourly, daily) and by dimensions.

### 5. Hourly Sales Trend

- **Business Definition:** Sales performance broken down by hour of the day, compared to previous periods.
- **Logic (SQL):**
  ```sql
  SELECT
      EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
      SUM(gmv) as sales
  FROM fact_orders
  GROUP BY 1
  ```

### 5.1 Hourly Heatmap (Day of Week Analysis)

- **Business Definition:** Sales intensity by Hour of Day and Day of Week.
- **Logic (SQL):**
  ```sql
  SELECT
      EXTRACT(HOUR FROM created_on) as hour_of_day,
      EXTRACT(DOW FROM created_on) as day_of_week, -- 0=Sunday
      COUNT(*) as order_count,
      SUM(total) as revenue
  FROM fact_orders
  GROUP BY 1, 2
  ORDER BY 2, 1
  ```

### 6. Sales by Channel

- **Business Definition:** Revenue breakdown by acquisition channel (e.g., Website, Mobile App, Partner).
- **Logic (SQL):**
  ```sql
  SELECT
      channel_name,
      SUM(total) as revenue
  FROM fact_orders
  JOIN dim_channels USING (channel_key) -- or source_channel column
  GROUP BY 1
  ```

## Context: Product Performance

> **Description:** Best selling products and category performance.

### 7. Top Selling Products

- **Business Definition:** Ranking of products by revenue or units sold.
- **Logic (SQL):**
  ```sql
  SELECT
      p.product_name,
      SUM(oli.quantity) as units_sold,
      SUM(oli.line_amount) as revenue
  FROM order_line_items oli
  JOIN dim_products p USING (product_id)
  GROUP BY 1
  ORDER BY revenue DESC
  ```

## Context: Customer Engagement

### 8. New vs Returning Customers

- **Business Definition:** Categorization of orders based on whether the customer has purchased before.
- **Logic (SQL):**
  ```sql
  CASE
    WHEN date(c.first_order_date) = current_date THEN 'New'
    ELSE 'Returning'
  END
  ```
  END
  ```

  ```

## Context: Payment Operations

### 9. Payment Method Distribution

- **Business Definition:** Transaction count and volume by payment method (Credit Card, COD, etc.).
- **Logic (SQL):**
  ```sql
  SELECT
      pm.payment_method_name,
      COUNT(*) as transaction_count,
      SUM(p.amount) as total_amount
  FROM payments p
  JOIN payment_methods pm USING (payment_method_id)
  WHERE p.status = 'completed'
  GROUP BY 1
  ```

### 10. Payment Status

- **Business Definition:** Tracking of payment success/failure.
- **Logic (SQL):**
  ```sql
  SELECT payment_status, COUNT(*), SUM(total) FROM orders GROUP BY 1
  ```

## Context: Promotions & Discounts

### 11. Discount Impact

- **Business Definition:** Value of discounts given and percentage of orders discounted.
- **Logic (SQL):**
  ```sql
  SUM(CASE WHEN total_discount > 0 THEN 1 ELSE 0 END) as discounted_orders,
  SUM(total_discount) as total_discounts,
  AVG(total_discount * 100.0 / NULLIF(total, 0)) as avg_discount_pct
  ```

### 12. Promotion Performance

- **Business Definition:** Revenue and usage by specific promotion campaign.
- **Logic (SQL):**
  ```sql
  SELECT
      pr.promotion_name,
      COUNT(DISTINCT o.order_id) as usage_count,
      SUM(o.total) as revenue_with_promo
  FROM orders o
  JOIN promotion_redemptions pr USING (order_id)
  GROUP BY 1
  ```

## Context: Location Analysis

### 13. Sales by Region/Location

- **Business Definition:** Revenue performance by geographic unit.
- **Logic (SQL):**
  ```sql
  SELECT
      l.region,
      l.location_name,
      SUM(o.total) as revenue
  FROM fact_orders o
  JOIN dim_locations l USING (location_id)
  GROUP BY 1, 2
  ```

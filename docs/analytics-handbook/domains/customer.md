# Customer Domain

> **Owner:** Marketing / Customer Success
> **Update Frequency:** Daily / Monthly

## Context: Acquisition & Value

> **Description:** Metrics related to acquiring customers and their lifetime value.
> **dbt Source:** `dim_customers`, `fact_orders`

### 1. Customer Acquisition Cost (CAC)

- **Business Definition:** Average cost to acquire a new customer.
- **Logic (SQL):**
  ```sql
  Marketing_Spend / New_Customers
  ```

### 2. Customer Lifetime Value (CLV)

- **Business Definition:** Projected revenue from a customer over their lifetime (e.g., 3 years).
- **Logic (SQL):**
  ```sql
  -- AOV * Purchase Frequency * Lifespan
  (avg_order_value) * (purchase_freq_annual) * (lifespan_years)
  ```
- **Detailed Logic (dbt CTE):**
  ```sql
  WITH customer_metrics AS (
      SELECT
          c.customer_id,
          COUNT(DISTINCT o.order_id) as order_count,
          SUM(o.order_total) as total_revenue,
          DATEDIFF('day', c.first_order_date, c.last_order_date) as lifespan
      FROM dim_customers c JOIN fact_orders o ON c.customer_id = o.customer_id
      GROUP BY 1
  )
  SELECT
      (total_revenue / order_count) * -- AOV
      (order_count * 365.0 / lifespan) * -- Freq
      3 -- 3 year projection
  FROM customer_metrics
  ```
  _See `clv_calc` CTE in Customer Playbook archives for full logic._

### 3. ARPU (Average Revenue Per User)

- **Business Definition:** Total Revenue divided by Active Users.
- **Logic (SQL):**
  ```sql
  SUM(Revenue) / COUNT(Active_Users)
  ```

## Context: Retention & Engagement

> **Description:** Metrics tracking user activity and churn.

### 4. Monthly Active Users (MAU)

- **Business Definition:** Unique users with activity in the last 30 days.
- **Logic (SQL):**
  ```sql
  COUNT(DISTINCT customer_id) WHERE last_active_date >= CURRENT_DATE - 30
  ```

### 5. Retention Rate

- **Business Definition:** Percentage of users who return in a subsequent period.
- **Logic (SQL):**
  ```sql
  -- Cohort Analysis Logic
  (Customers_End / Customers_Start) * 100
  ```
- **Detailed Logic (SQL):**
  ```sql
  WITH cohort_activity AS (
      SELECT
          DATE_TRUNC('month', first_order_date) as cohort_month,
          DATE_TRUNC('month', o.order_date) as activity_month,
          COUNT(DISTINCT c.customer_id) as customers
      FROM dim_customers c JOIN fact_orders o USING (customer_id)
      GROUP BY 1, 2
  )
  ...
  ```

### 6. Churn Rate

- **Business Definition:** Percentage of customers lost over a period.
- **Logic (SQL):**
  ```sql
  Lost_Customers / Total_Customers * 100
  ```

## Context: Segmentation

> **Description:** Grouping customers by behavior.

### 7. RFM Segment

- **Business Definition:** Recency, Frequency, Monetary segmentation (Champions, Loyal, At Risk, etc.).
- **Logic (SQL):**
  ```sql
  -- Logic requires calculating R, F, M scores (NTILE) and mapping to segments.
  WITH rfm_calc AS (
      SELECT
          customer_id,
          NTILE(5) OVER (ORDER BY recency DESC) as r_score,
          NTILE(5) OVER (ORDER BY frequency) as f_score,
          NTILE(5) OVER (ORDER BY monetary) as m_score
      FROM customer_metrics
  )
  SELECT
      CASE
          WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
          WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
          WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
          ELSE 'Need Attention'
      END as segment
  FROM rfm_calc
  ```

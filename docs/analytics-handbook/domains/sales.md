# Sales Domain

> **Owner:** Sales Team / Data Team
> **Update Frequency:** Real-time / Daily

## Context: Order Performance

> **Description:** Core metrics regarding order volume, revenue, and efficiency.
> **dbt Source:** `fact_orders`
> **Grain:** Per Order

### 1. Gross Revenue (GMV)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
> **Terminology Guide:** [Revenue Terminology](../guides/revenue_terminology.md)

- **Business Definition:** Tổng giá trị hàng hóa theo giá niêm yết, trước chiết khấu. Dùng để đánh giá quy mô giao dịch.
- **Logic (Metabase SQL):**
  ```sql
  SUM(gross_revenue)
  ```
- **Metabase Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Gross Revenue` (Aggregation: Sum)

### 2. Net Revenue

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Doanh thu thuần — số tiền khách trả cho hàng hóa sau chiết khấu, trước thuế. Đây là con số quan trọng nhất cho phân tích kinh doanh.
- **Logic (Metabase SQL):**
  ```sql
  SUM(net_revenue)
  ```
- **Metabase Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Net Revenue` (Aggregation: Sum)

### 2b. Total Collected

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Tổng tiền thu từ khách (bao gồm thuế VAT). Dùng để đối soát với kế toán/ngân hàng.
- **Logic (Metabase SQL):**
  ```sql
  SUM(total_collected)
  ```
- **Metabase Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Total Collected` (Aggregation: Sum)

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
  SUM(net_revenue) / COUNT(DISTINCT order_id)
  ```

## Available Dashboards

| Dashboard Name                | Audience              | Purpose                                                        | Link                            |
| :---------------------------- | :-------------------- | :------------------------------------------------------------- | :------------------------------ |
| **Sales Executive Dashboard** | Executives / Managers | High-level monthly overview of revenue, channels, and targets. | [Metabase ID 37](/dashboard/37) |
| **Daily Sales Dashboard**     | Ops / Sales Reps      | Real-time monitoring of today's performance — 4 tabs: Overview, Channels, Products, Customers & Payments. | [Metabase ID 2](/dashboard/2) |
| **Yesterday's Sales Dashboard** | Ops / Store Managers | Finalized yesterday review — 4 tabs: Overview, Channels, Products, Customers & Payments. | [Metabase ID 5](/dashboard/5) |
| **Today's Orders List**         | Ops / Sales Reps    | Order-level list for real-time reconciliation with Sapo.        | TBD                             |
| **Yesterday's Orders List**     | Ops / Store Managers | Finalized order-level list for reconciliation with Sapo.        | TBD                             |
| **CEO Weekly Pulse**            | CEO / Founders       | 5-min weekly check-in: revenue pace, channel shifts, customer health. | TBD                       |
| **CEO Monthly Scorecard**       | CEO / Board          | Comprehensive monthly review: targets, channels, segments, efficiency. | TBD                      |
| **Marketing Weekly Tracker**    | Marketing Manager    | Weekly channel performance, acquisition, promotions, social commerce.  | TBD                      |
| **Marketing Monthly Analysis**  | Marketing / CMO      | Monthly deep dive: channel strategy, cohort retention, campaign ROI.   | TBD                      |
| **Sales Ops Weekly Review**     | Sales Ops / CS Lead  | Weekly order processing, team performance, channel workload.           | TBD                      |
| **Sales Ops Monthly Summary**   | Sales Ops / Ops Mgr  | Monthly operational efficiency, staff KPIs, payment reconciliation.    | TBD                      |

## Composite Metrics

### Health Score (Business Health)

> **Guide:** [Health Score — Chỉ số Sức khỏe Kinh doanh](../guides/health_score.md)

- **Business Definition:** Điểm tổng hợp 0-100 đánh giá sức khỏe kinh doanh dựa trên 4 chiều: Revenue Momentum (WoW), Order Momentum (WoW), Customer Loyalty (Returning Rate), AOV Stability. Hiển thị tại tab Tổng quan của Daily/Yesterday dashboards.
- **Thang điểm:** 75-100 Khỏe mạnh | 50-74 Cần chú ý | 0-49 Báo động
- **Source Tables:** `fact_orders`, `dim_customers`

## Related Playbooks

| Playbook                                                           | Description                                                                           |
| :----------------------------------------------------------------- | :------------------------------------------------------------------------------------ |
| **[Sales Monthly Review](../playbooks/sales_monthly_review.md)**   | Guide for conducting the Monthly Business Review (MBR) using the Executive Dashboard. |
| **[Yesterday's Sales Ops](../playbooks/sales_yesterday_operation.md)** | Review finalized yesterday's performance with day-over-day comparisons.           |
| **[Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)** | Order-level listing for BI vs Sapo reconciliation (Today & Yesterday).    |
| **[Promotion Analysis](../playbooks/sales_promotion_analysis.md)** | Deep dive methodologies for validating campaign ROI and discount strategies.          |
| **[Customer Support Domain](../domains/customer_support.md)**      | For "Social Commerce" and Inbound Sales specific metrics.                             |
| **[CEO Weekly Pulse](../playbooks/ceo_weekly_pulse.md)**           | CEO's Monday morning 5-minute weekly check-in dashboard.                              |
| **[CEO Monthly Scorecard](../playbooks/ceo_monthly_scorecard.md)** | CEO's comprehensive monthly performance scorecard.                                    |
| **[Marketing Weekly Tracker](../playbooks/marketing_weekly_tracker.md)** | Marketing Manager's weekly channel & acquisition tracker.                       |
| **[Marketing Monthly Analysis](../playbooks/marketing_monthly_analysis.md)** | Marketing's monthly strategic analysis with cohort & campaign deep dive.   |
| **[Sales Ops Weekly Review](../playbooks/sales_ops_weekly_review.md)** | CS/Sales Ops weekly operational review & team performance.                        |
| **[Sales Ops Monthly Summary](../playbooks/sales_ops_monthly_summary.md)** | CS/Sales Ops monthly operations summary & staff KPIs.                        |

## Context: Order List (Reconciliation)

> **Description:** Row-level order listing for cross-checking BI records against the source sales system (Sapo). Used to verify data completeness and correctness.
> **dbt Source:** `fact_orders` joined with `dim_channels`, `dim_customers`
> **Grain:** Per Order

### 17. Order Detail List

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Detailed order-level listing with key fields for reconciliation: order ID/code, timestamps, amounts, statuses, customer info, channel, and payment method.
- **Key Fields:**

| Field | Source | Purpose |
| :---- | :----- | :------ |
| `order_id` | `fact_orders` | Primary business key — match with Sapo order ID |
| `order_code` | `stg_sapo_orders` | Human-readable code (e.g. `#1234`) — visible in Sapo UI |
| `order_timestamp` | `fact_orders.order_timestamp` | Order creation time |
| `status` | `fact_orders` | Order status (open, completed, cancelled) |
| `payment_status` | `fact_orders` | paid, pending, refunded |
| `fulfillment_status` | `fact_orders` | fulfilled, unfulfilled, returned |
| `net_revenue` | `fact_orders` | Doanh thu thuần (sau chiết khấu, trước thuế) |
| `total_collected` | `fact_orders` | Tổng thu từ khách (gồm thuế) |
| `discount_amount` | `fact_orders` | Chiết khấu |
| `channel_name` | `dim_channels` | Sales channel (POS, Web, Shopee, etc.) |
| `customer_name` | `stg_sapo_orders` | Customer name for quick identification |
| `customer_phone` | `stg_sapo_orders` | Phone for cross-referencing |
| `payment_method_name` | `stg_sapo_orders` | Cash, Card, Transfer, etc. |
| `location_name` | `stg_sapo_orders` | Store/branch that processed the order |

- **Playbook:** [Orders List Reconciliation](../playbooks/orders_list_reconciliation.md)

## Context: Operational Trends

> **Description:** Analysis of sales patterns over time (hourly, daily) and by dimensions.

### 6. Hourly Sales Trend

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Sales performance broken down by hour of the day, compared to previous periods.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      EXTRACT(HOUR FROM order_timestamp) as hour_of_day,
      SUM(net_revenue) as sales
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
      SUM(net_revenue) as revenue
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
      SUM(net_revenue) as revenue
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
  SELECT payment_status, COUNT(*), SUM(total_collected) FROM fact_orders GROUP BY 1
  ```

## Context: Promotions & Discounts

> **Playbook:** [Promotion Analysis](../playbooks/sales_promotion_analysis.md)

### 13. Discount Impact

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Value of discounts given and percentage of orders discounted.
- **Logic (Metabase SQL):**
  ```sql
  SUM(CASE WHEN discount_amount > 0 THEN 1 ELSE 0 END) as discounted_orders,
  SUM(discount_amount) as total_discounts,
  AVG(discount_amount * 100.0 / NULLIF(gross_revenue, 0)) as avg_discount_pct
  ```

### 14. Promotion Performance

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Revenue and usage by specific promotion campaign.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      pr.promotion_name,
      COUNT(DISTINCT o.order_id) as usage_count,
      SUM(o.net_revenue) as revenue_with_promo
  FROM fact_orders o
  JOIN promotion_redemptions pr USING (order_id)
  GROUP BY 1
  ```

## Context: Sales Targets

> **Description:** Comparison of actual performance against defined goals.
> **dbt Source:** `fact_targets`
> **Input Guide:** [Targets Sheet Guide](../../guides/targets-sheet.md)

`fact_targets` stores target rules with flexible cycle types (`daily`, `weekly`, `monthly`, `quarterly`, `yearly`) and scope filters (branch, team, staff, channel, product). Each target has a `cycle_start_date`, `cycle_end_date`, and `cycle_type` derived automatically from the input sheet.

### 15. Target Achievement Rate

> **dbt Model:** [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)

- **Business Definition:** Percentage of target achieved (Actual Revenue / Target Revenue) within a cycle.
- **Logic (Metabase SQL):**
  ```sql
  SUM(actual_revenue) / NULLIF(SUM(target_val), 0)
  ```

### 16. Variance to Target

> **dbt Model:** [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)

- **Business Definition:** Absolute difference between Actual and Target within a cycle.
- **Logic (Metabase SQL):**
  ```sql
  SUM(actual_revenue) - SUM(target_val)
  ```

> **Implementation Note:**
> Do not attempt to join `fact_orders` and `fact_targets` directly in a Native Query as they have different grains (Order vs Cycle/Scope).
> **Recommended Approach:** Create a **Metabase Model** (or dbt mart `mart_sales_actual_vs_target`) to pre-aggregate `fact_orders` to match the target's cycle and scope before joining with `fact_targets`.

## Context: Location Analysis

### 15. Sales by Region/Location

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Revenue performance by geographic unit.
- **Logic (Metabase SQL):**
  ```sql
  SELECT
      l.region,
      l.location_name,
      SUM(o.net_revenue) as revenue
  FROM fact_orders o
  JOIN dim_locations l USING (location_id)
  GROUP BY 1, 2
  ```

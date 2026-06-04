# Sales Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** Sales Team / Data Team
> **Update Frequency:** Real-time / Daily
> **Cập nhật:** 2026-04-19
> **Xem thêm:** [Report Segmentation Guide](../guides/report_segmentation.md)

---

## Scope Definitions (QUAN TRỌNG)

> **Tham chiếu:** [Report Segmentation Guide](../guides/report_segmentation.md) — Chi tiết về 3-layer architecture

Tất cả metrics trong domain này PHẢI được apply đúng scope tùy theo dashboard layer:

### Base Scopes

| Scope | Filter SQL | Dùng cho |
|-------|------------|----------|
| **scope_sales** | `is_sales_channel = true AND status NOT IN ('CANCELLED', 'Voided')` | Layer 1 Executive [All] |
| **scope_retail** | scope_sales `AND customer_type = 'RETAIL'` | Layer 2 Retail [Retail] |
| **scope_b2b** | scope_sales `AND customer_type IN ('WHOLESALE', 'PARTNER')` | Layer 2 B2B [B2B] |

### Scope Requirements by Metric

| Metric | Scope Requirement | Lý do |
|--------|-------------------|-------|
| **Discount Rate, Discount Amount** | BẮT BUỘC scope_retail | B2B discount = giá sỉ cố định, không phải promotion |
| **Promotion ROI, Promo Analysis** | BẮT BUỘC scope_retail | B2B không có promotion |
| **AOV (Average Order Value)** | scope_retail HOẶC scope_b2b | Không mix 2 mức giá khác nhau |
| **Revenue, Orders (overview)** | scope_sales | Cần full picture |
| **Customer Metrics** | scope_retail | Retail customer focus |

### Cảnh báo: Data Pollution

```
❌ KHÔNG:
SELECT SUM(discount_amount) FROM fact_orders
→ Trộn lẫn promotion discount (retail) với giá sỉ (B2B) = sai lệch

✅ ĐÚNG:
SELECT SUM(discount_amount) FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE c.customer_type = 'RETAIL'
```

---
## Context: Order Performance

> **Description:** Core metrics regarding order volume, revenue, and efficiency.
> **dbt Source:** `fact_orders`
> **Grain:** Per Order

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Order Performance | Are revenue, order volume, and order value moving because of volume, value, or order quality? | 1. Gross Revenue (GMV), 2. Net Revenue, 2b. Total Collected, 3. Return Rate & Count, 4. Total Orders, 5. AOV (Average Order Value) | `fact_orders` | None documented |

### Analytical Questions

#### Q1. Order Performance Readiness

- **Question:** Are revenue, order volume, and order value moving because of volume, value, or order quality?
- **Definition:** This question defines whether `Order Performance` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** revenue/order performance, lagging, volume/value.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 1. Gross Revenue (GMV), 2. Net Revenue, 2b. Total Collected, 3. Return Rate & Count, 4. Total Orders, 5. AOV (Average Order Value)

### Metrics

#### 1. Gross Revenue (GMV)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
> **Terminology Guide:** [Revenue Terminology](../guides/revenue_terminology.md)

- **Business Definition:** Tổng giá trị hàng hóa theo giá bán, trước chiết khấu. Dùng để đánh giá quy mô giao dịch. **Sapo giá bán đã gồm VAT** — gross_revenue = total_amount + discount_amount. Xem [Revenue Terminology](../guides/revenue_terminology.md).
- **Logic (SQL):**
  ```sql
  SUM(gross_revenue)
  ```
- **Source Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Gross Revenue` (Aggregation: Sum)

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2. Net Revenue

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Doanh thu thuần — số tiền khách trả cho hàng hóa sau chiết khấu, **đã trừ VAT** (= total_amount − vat_amount). VAT nhúng trong giá bán Sapo — net_revenue là con số P&L so sánh như-cho-như với giá vốn. Đây là con số quan trọng nhất cho phân tích kinh doanh. Xem [Revenue Terminology](../guides/revenue_terminology.md).
- **Logic (SQL):**
  ```sql
  SUM(net_revenue)
  ```
- **Source Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Net Revenue` (Aggregation: Sum)

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2b. Total Collected

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Tổng tiền thu từ khách (bao gồm thuế VAT). Dùng để đối soát với kế toán/ngân hàng.
- **Logic (SQL):**
  ```sql
  SUM(total_collected)
  ```
- **Source Mapping:**
  - **Table:** `fact_orders`
  - **Field:** `Total Collected` (Aggregation: Sum)

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 3. Return Rate & Count

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Count of returned orders.
- **Logic (SQL):**
- **Logic (SQL):**
  ```sql
  COUNT(CASE WHEN fulfillment_status = 'RETURNED' THEN 1 END)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 4. Total Orders

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Count of unique confirmed orders.
- **Logic (SQL):**
  ```sql
  COUNT(DISTINCT order_id)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** count
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 5. AOV (Average Order Value)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Average revenue generated per order.
- **Logic (SQL):**
  ```sql
  SUM(net_revenue) / COUNT(DISTINCT order_id)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Available Dashboards

> **Naming convention:** Dashboard có suffix `[All]`, `[Retail]`, `[B2B]`, hoặc `[Cross]` để chỉ scope. Xem [Report Segmentation Guide](../guides/report_segmentation.md).

#### Layer 1 — Executive [All]

| Dashboard Name | Scope | Audience | Purpose |
|:---|:---|:---|:---|
| **CEO Weekly Pulse [All]** | scope_sales | CEO / Founders | 5-min weekly check-in: revenue pace, channel shifts, customer health |
| **CEO Monthly Scorecard [All]** | scope_sales | CEO / Board | Comprehensive monthly review: targets, channels, segments, efficiency |
| **Order Profitability [All]** | scope_sales | CEO / CFO / Sales Director | P&L per order, gross margin, channel net profit |

#### Layer 2 — Retail Operations [Retail]

| Dashboard Name | Scope | Audience | Purpose |
|:---|:---|:---|:---|
| **Daily Sales [Retail]** | scope_retail | Ops / Sales Reps | Real-time monitoring — 4 tabs: Overview, Channels, Products, Customers |
| **Yesterday's Sales [Retail]** | scope_retail | Ops / Store Managers | Finalized yesterday review |
| **Today's Orders [Retail]** | scope_retail | Ops / Sales Reps | Order-level list for reconciliation |
| **Yesterday's Orders [Retail]** | scope_retail | Ops / Store Managers | Finalized order-level list |
| **Promotion Analysis [Retail]** | scope_retail | Marketing / Sales Ops | Promotion ROI, discount analysis — **BẮT BUỘC scope_retail** |
| **Sales Ops Weekly [Retail]** | scope_retail | Sales Ops / CS Lead | Weekly order processing, team performance |
| **Sales Ops Monthly [Retail]** | scope_retail | Sales Ops / Ops Mgr | Monthly operational efficiency, staff KPIs |

#### Layer 2 — B2B Operations [B2B]

| Dashboard Name | Scope | Audience | Purpose |
|:---|:---|:---|:---|
| **B2B Daily Sales [B2B]** | scope_b2b | B2B Sales | Daily wholesale/partner orders |
| **B2B Orders Tracking [B2B]** | scope_b2b | B2B Sales | Order list, credit tracking |
| **Partner Performance [B2B]** | scope_b2b | B2B Manager | CTV/Partner metrics |
| **B2B Margin Analysis [B2B]** | scope_b2b | Finance / B2B Sales | Wholesale margin analysis |

#### Layer 2 — Marketing & Customers [Retail]

| Dashboard Name | Scope | Audience | Purpose |
|:---|:---|:---|:---|
| **Marketing Weekly Tracker [Retail]** | scope_retail | Marketing Manager | Weekly channel performance, acquisition, promotions |
| **Marketing Monthly Analysis [Retail]** | scope_retail | Marketing / CMO | Monthly deep dive: channel strategy, cohort retention |

#### Layer 3 — Analytics [Cross]

| Dashboard Name | Scope | Audience | Purpose |
|:---|:---|:---|:---|
| **Channel Profitability [Cross]** | scope_sales + breakdown | Analysts / Leadership | Margin comparison by customer_type |
## Composite Metrics

#### Health Score (Business Health)

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

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Order List (Reconciliation) | Is the order-level list complete enough to reconcile BI records against Sapo? | 17. Order Detail List | `fact_orders` joined with `dim_channels`, `dim_customers` | None documented |

### Analytical Questions

#### Q1. Order List (Reconciliation) Readiness

- **Question:** Is the order-level list complete enough to reconcile BI records against Sapo?
- **Definition:** This question defines whether `Order List (Reconciliation)` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** operational reconciliation, detail grain.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 17. Order Detail List

### Metrics

#### 17. Order Detail List

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Detailed order-level listing with key fields for reconciliation: order ID/code, timestamps, amounts, statuses, customer info, channel, and payment method.
- **Key Fields:**

| Field | Source | Purpose |
| :---- | :----- | :------ |
| `order_id` | `fact_orders` | Primary business key — match with Sapo order ID |
| `order_code` | `stg_sapo_orders` | Human-readable code (e.g. `#1234`) — visible in Sapo UI |
| `ordered_at` | `fact_orders.ordered_at` | Order creation time |
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

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Operational Trends

> **Description:** Analysis of sales patterns over time (hourly, daily) and by dimensions.

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Operational Trends | How do sales patterns change by hour, day, and channel? | 6. Hourly Sales Trend, 7. Hourly Heatmap (Day of Week Analysis), 8. Sales by Channel | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Operational Trends Readiness

- **Question:** How do sales patterns change by hour, day, and channel?
- **Definition:** This question defines whether `Operational Trends` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** operational cadence, leading/lagging mix.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 6. Hourly Sales Trend, 7. Hourly Heatmap (Day of Week Analysis), 8. Sales by Channel

### Metrics

#### 6. Hourly Sales Trend

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Sales performance broken down by hour of the day, compared to previous periods.
- **Logic (SQL):**
  ```sql
  SELECT
      EXTRACT(HOUR FROM ordered_at) as hour_of_day,
      SUM(net_revenue) as sales
  FROM fact_orders
  GROUP BY 1
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 7. Hourly Heatmap (Day of Week Analysis)

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Sales intensity by Hour of Day and Day of Week.
- **Logic (SQL):**
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

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 8. Sales by Channel

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Revenue breakdown by acquisition channel (e.g., Website, Mobile App, Partner).
- **Logic (SQL):**
  ```sql
  SELECT
      channel_name,
      SUM(net_revenue) as revenue
  FROM fact_orders
  JOIN dim_channels USING (channel_key) -- or source_channel column
  GROUP BY 1
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Product Performance

> **Description:** Best selling products and category performance.

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Product Performance | Which products are driving volume, revenue, and margin? | 9. Top Selling Products | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Product Performance Readiness

- **Question:** Which products are driving volume, revenue, and margin?
- **Definition:** This question defines whether `Product Performance` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** merchandising performance, volume/value/quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 9. Top Selling Products

### Metrics

#### 9. Top Selling Products

> **dbt Model:** [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql)

- **Business Definition:** Ranking of products by revenue or units sold.
- **Logic (SQL):**
  ```sql
  SELECT
      p.product_name,
      SUM(oli.quantity) as units_sold,
      SUM(oli.net_revenue) as revenue
  FROM fact_sales oli -- mapped from order_line_items
  JOIN dim_products p USING (product_id)
  GROUP BY 1
  ORDER BY revenue DESC
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Customer Engagement

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Customer Engagement | How do new and returning customers contribute to growth? | 10. New vs Returning Customers | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Customer Engagement Readiness

- **Question:** How do new and returning customers contribute to growth?
- **Definition:** This question defines whether `Customer Engagement` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** customer behavior, leading/lagging mix.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 10. New vs Returning Customers

### Metrics

#### 10. New vs Returning Customers

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Categorization of orders based on whether the customer has purchased before.
- **Logic (SQL):**
  ```sql
  CASE
    WHEN date(c.first_order_date) = current_date THEN 'New'
    ELSE 'Returning'
  END
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Payment Operations

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Payment Operations | Do payment methods or statuses create operational or reconciliation risk? | 11. Payment Method Distribution, 12. Payment Status | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Payment Operations Readiness

- **Question:** Do payment methods or statuses create operational or reconciliation risk?
- **Definition:** This question defines whether `Payment Operations` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** finance operations, operational quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 11. Payment Method Distribution, 12. Payment Status

### Metrics

#### 11. Payment Method Distribution

> **dbt Model:** [`stg_sapo_payments`](../../../transformation/models/staging/stg_sapo_payments.sql)

- **Business Definition:** Transaction count and volume by payment method (Credit Card, COD, etc.).
- **Logic (SQL):**
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

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 12. Payment Status

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Tracking of payment success/failure.
- **Logic (SQL):**
  ```sql
  SELECT payment_status, COUNT(*), SUM(total_collected) FROM fact_orders GROUP BY 1
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Promotions & Discounts

> **Playbook:** [Promotion Analysis](../playbooks/sales_promotion_analysis.md)

> **⚠️ SCOPE REQUIREMENT: BẮT BUỘC `scope_retail` (`customer_type = 'RETAIL'`)**
>
> Discount của B2B (WHOLESALE, PARTNER) là **giá sỉ cố định** (40-50%), KHÔNG phải promotion.
> Nếu không filter, kết quả discount analysis sẽ sai lệch nghiêm trọng.
>
> Xem: [Report Segmentation Guide](../guides/report_segmentation.md#42-quy-tắc-vàng)

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Promotions & Discounts | Do discounts and promotions create enough incremental value to justify their cost? | 13. Discount Impact, 14. Promotion Performance | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Promotions & Discounts Readiness

- **Question:** Do discounts and promotions create enough incremental value to justify their cost?
- **Definition:** This question defines whether `Promotions & Discounts` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** promotion efficiency, value/quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 13. Discount Impact, 14. Promotion Performance

### Metrics

#### 13. Discount Impact

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
> **Required Scope:** scope_retail (`customer_type = 'RETAIL'`)

- **Business Definition:** Value of discounts given and percentage of orders discounted. **Chỉ áp dụng cho retail orders.**
- **Logic (SQL):**
  ```sql
  -- BẮT BUỘC filter customer_type = 'RETAIL'
  SELECT
      SUM(CASE WHEN discount_amount > 0 THEN 1 ELSE 0 END) as discounted_orders,
      SUM(discount_amount) as total_discounts,
      AVG(discount_amount * 100.0 / NULLIF(gross_revenue, 0)) as avg_discount_pct
  FROM fact_orders o
  JOIN dim_customers c ON o.customer_key = c.customer_key
  WHERE c.customer_type = 'RETAIL'
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 14. Promotion Performance

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
> **Required Scope:** scope_retail (`customer_type = 'RETAIL'`)

- **Business Definition:** Revenue and usage by specific promotion campaign. **Chỉ áp dụng cho retail orders.**
- **Logic (SQL):**
  ```sql
  -- BẮT BUỘC filter customer_type = 'RETAIL'
  SELECT
      pr.promotion_name,
      COUNT(DISTINCT o.order_id) as usage_count,
      SUM(o.net_revenue) as revenue_with_promo
  FROM fact_orders o
  JOIN promotion_redemptions pr USING (order_id)
  JOIN dim_customers c ON o.customer_key = c.customer_key
  WHERE c.customer_type = 'RETAIL'
  GROUP BY 1
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Sales Targets

> **Description:** Comparison of actual performance against defined goals.
> **dbt Source:** `fact_targets`
> **Input Guide:** [Targets Sheet Guide](../../guides/targets-sheet.md)

`fact_targets` stores target rules with flexible cycle types (`daily`, `weekly`, `monthly`, `quarterly`, `yearly`) and scope filters (branch, team, staff, channel, product). Each target has a `cycle_start_date`, `cycle_end_date`, and `cycle_type` derived automatically from the input sheet.

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Sales Targets | Is sales performance ahead of or behind target pace? | 15. Target Achievement Rate, 16. Variance to Target | `fact_targets` | None documented |

### Analytical Questions

#### Q1. Sales Targets Readiness

- **Question:** Is sales performance ahead of or behind target pace?
- **Definition:** This question defines whether `Sales Targets` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** target tracking, strategic lagging.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 15. Target Achievement Rate, 16. Variance to Target

### Metrics

#### 15. Target Achievement Rate

> **dbt Model:** [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)

- **Business Definition:** Percentage of target achieved (Actual Revenue / Target Revenue) within a cycle.
- **Logic (SQL):**
  ```sql
  SUM(actual_revenue) / NULLIF(SUM(target_val), 0)
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 16. Variance to Target

> **dbt Model:** [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)

- **Business Definition:** Absolute difference between Actual and Target within a cycle.
- **Logic (SQL):**
  ```sql
  SUM(actual_revenue) - SUM(target_val)
  ```

> **Implementation Note:**
> Do not attempt to join `fact_orders` and `fact_targets` directly in a Native Query as they have different grains (Order vs Cycle/Scope).
> **Recommended Approach:** Create a **semantic data model** (or dbt mart `mart_sales_actual_vs_target`) to pre-aggregate `fact_orders` to match the target's cycle and scope before joining with `fact_targets`.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Location Analysis

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Location Analysis | Which regions or locations are contributing to or dragging performance? | 15. Sales by Region/Location | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Location Analysis Readiness

- **Question:** Which regions or locations are contributing to or dragging performance?
- **Definition:** This question defines whether `Location Analysis` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** location performance, comparative.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 15. Sales by Region/Location

### Metrics

#### 15. Sales by Region/Location

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Revenue performance by geographic unit.
- **Logic (SQL):**
  ```sql
  SELECT
      l.region,
      l.location_name,
      SUM(o.net_revenue) as revenue
  FROM fact_orders o
  JOIN dim_locations l USING (location_id)
  GROUP BY 1, 2
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

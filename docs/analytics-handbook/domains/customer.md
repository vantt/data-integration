# Customer Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** Marketing / Customer Success
> **Update Frequency:** Daily / Monthly
> **Cập nhật:** 2026-06-12
> **Xem thêm:** [Customer Segmentation](../../context/customer-segmentation.md), [Report Segmentation Guide](../guides/report_segmentation.md)

---

## Scope & Segmentation (QUAN TRỌNG)

### customer_type — Chiều phân loại quan trọng nhất

`customer_type` quyết định bản chất quan hệ với công ty, ảnh hưởng đến cách phân tích:

| customer_type | Bản chất | Ảnh hưởng đến phân tích |
|---------------|----------|-------------------------|
| **RETAIL** | Khách lẻ B2C | Default scope cho Marketing, Customer Ops |
| **WHOLESALE** | Khách sỉ | B2B analysis, giá sỉ ≠ promotion |
| **PARTNER** | CTV, đối tác, ký gửi | B2B analysis, chính sách riêng |
| **STAFF** | Nhân viên | Loại khỏi L2 analysis |
| **KOL** | Influencer | Loại khỏi L2 analysis |
| **CROSSBORDER** | Đơn US giao hàng hộ | Loại khỏi mọi sales scope — đơn nằm trên kênh `is_sales_channel=false` |

**Lưu ý CROSSBORDER:** CROSSBORDER (đơn US giao hộ) bị loại khỏi mọi sales scope vì đơn nằm trên kênh `is_sales_channel=false`. Customer của Sapo = người mua (VN); người nhận không phải customer. CROSSBORDER không thuộc scope_sales, scope_retail, hay scope_b2b.

### Default Scope cho Customer Metrics

Hầu hết customer metrics (Retention, MAU, Cohort, CAC, CLV) áp dụng cho **retail customers**:

```sql
-- scope_retail (mặc định cho customer domain)
WHERE c.customer_type = 'RETAIL'
```

**Lý do:**
- Marketing target retail customers
- Retention concept khác nhau giữa B2C vs B2B
- CLV calculation assumptions khác nhau
- B2B customer journey khác flow

### Khi nào KHÔNG filter customer_type?

- Layer 1 Executive dashboards (scope_sales [All])
- Cross-segment analysis (Layer 3 [Cross])
- Total customer count cho reporting

---
## Context: Acquisition & Value

> **Description:** Metrics related to acquiring customers and their lifetime value.
> **dbt Source:** `dim_customers`, `fact_orders`

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Acquisition & Value | Are acquisition cost and customer value economically balanced? | 1. Customer Acquisition Cost (CAC), 2. Customer Lifetime Value (CLV), 3. ARPU (Average Revenue Per User) | `dim_customers`, `fact_orders` | None documented |

### Analytical Questions

#### Q1. Acquisition & Value Readiness

- **Question:** Are acquisition cost and customer value economically balanced?
- **Definition:** This question defines whether `Acquisition & Value` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** customer economics, value/strategic.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 1. Customer Acquisition Cost (CAC), 2. Customer Lifetime Value (CLV), 3. ARPU (Average Revenue Per User)

### Metrics

#### 1. Customer Acquisition Cost (CAC)

> **dbt Model:** `fact_marketing_spend` (Planned), `dim_customers`

- **Business Definition:** Average cost to acquire a new customer.
- **Logic (SQL):**
  ```sql
  Marketing_Spend / New_Customers
  ```
- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2. Customer Lifetime Value (CLV)

> **Phase 1 Status:** Ready (Historical LTV)
> **Phase 2 Status:** Planned (Projected CLV)
##### Phase 1: Historical LTV (Operational)

> **dbt Model:** [dim_customers](../../../transformation/models/marts/core/dim_customers.sql) - `lifetime_value`

- **Business Definition:** Total revenue generated by a customer from their first purchase to now.
- **Logic (SQL):**
  ```sql
  SUM(order_total) WHERE status = 'completed'
  ```
##### Phase 2: Projected CLV (Analytical)

> **dbt Model:** Not yet implemented (Planned for Advanced Analytics)

- **Business Definition:** Projected revenue from a customer over their lifetime (e.g., 3 years).
- **Phasing Note:** Recommended for Marketing strategy after Phase 1 is stable.
- **Logic (SQL):**
  ```sql
  -- AOV * Purchase Frequency * Lifespan
  (avg_order_spend) * (purchase_freq_annual) * (lifespan_years)
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
- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 3. ARPU (Average Revenue Per User)

> **dbt Model:** [fact_orders](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Total Revenue divided by Active Users.
- **Logic (SQL):**
  ```sql
  SUM(Revenue) / COUNT(Active_Users)
  ```
- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Retention & Engagement

> **Description:** Metrics tracking user activity and churn.
> **Default Scope:** scope_retail (`customer_type = 'RETAIL'`) — Retention concepts áp dụng chủ yếu cho retail customers.

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Retention & Engagement | Are customers returning and staying active in the expected cycle? | 4. Monthly Active Users (MAU), 5. Retention Rate, 6. Churn Rate | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Retention & Engagement Readiness

- **Question:** Are customers returning and staying active in the expected cycle?
- **Definition:** This question defines whether `Retention & Engagement` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** retention, leading/lagging mix.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 4. Monthly Active Users (MAU), 5. Retention Rate, 6. Churn Rate

### Metrics

#### 4. Monthly Active Users (MAU)

> **dbt Model:** [dim_customers](../../../transformation/models/marts/core/dim_customers.sql)
> **Recommended Scope:** scope_retail (`customer_type = 'RETAIL'`)

- **Business Definition:** Unique users with activity in the last 30 days.
- **Logic (SQL):**
  ```sql
  -- Retail MAU (recommended)
  SELECT COUNT(DISTINCT customer_key)
  FROM fact_orders o
  JOIN dim_customers c ON o.customer_key = c.customer_key
  WHERE o.ordered_at >= CURRENT_DATE - INTERVAL '30 days'
    AND c.customer_type = 'RETAIL'
    AND o.status NOT IN ('CANCELLED', 'Voided')
  ```
- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** count
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 5. Retention Rate

> **dbt Model:** [fact_orders](../../../transformation/models/marts/sales/fact_orders.sql)
> **Recommended Scope:** scope_retail (`customer_type = 'RETAIL'`)

- **Business Definition:** Percentage of users who return in a subsequent period. **B2B retention có logic khác (contract-based), nên tách riêng.**
- **See also:** [Cohort Framework](#context-cohort-framework) — cohort theo `first_order_month` (logic SQL dưới đây) chỉ là **1 axis**; khung đa chiều mở rộng sang entry_product / channel / basket / value + composite.
- **Logic (SQL):**
  ```sql
  -- Cohort Analysis Logic - Retail Only
  (Customers_End / Customers_Start) * 100
  ```
- **Detailed Logic (SQL):**
  ```sql
  WITH cohort_activity AS (
      SELECT
          DATE_TRUNC('month', c.first_order_date) as cohort_month,
          DATE_TRUNC('month', o.ordered_at) as activity_month,
          COUNT(DISTINCT c.customer_key) as customers
      FROM dim_customers c
      JOIN fact_orders o ON c.customer_key = o.customer_key
      WHERE c.customer_type = 'RETAIL'  -- scope_retail
      GROUP BY 1, 2
  )
  ...
  ```
- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 6. Churn Rate

> **dbt Model:** [dim_customers](../../../transformation/models/marts/core/dim_customers.sql)
> **Recommended Scope:** scope_retail (`customer_type = 'RETAIL'`)

- **Business Definition:** Percentage of customers lost over a period.
- **Logic (SQL):**
  ```sql
  -- Retail Churn Rate
  SELECT COUNT(*) FILTER (WHERE customer_status = 'Churned') * 100.0 / COUNT(*)
  FROM dim_customers
  WHERE customer_type = 'RETAIL'
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Cohort Framework

> **Description:** Khung cohort đa chiều — đo retention/value của khách theo **cách họ vào tệp**, không chỉ theo tháng mua đầu.
> **Default Scope:** scope_retail (`customer_type = 'RETAIL'`).
> **dbt Source:** `int_customer_entry_attributes` (entry-key, 1 dòng/khách) + `mart_cohort_retention` (long-format, parameterized) — **Planned (P2)**.
> **Grain:** `mart_cohort_retention` = 1 dòng / (cohort_dimension × cohort_value × window_type × period_n).
> **Status:** Design CHỐT 2026-06-12 (spec v1). Mart chưa build — đừng dùng làm reporting source tới khi P2 verify.

### Mental model (đọc trước)

Một **cohort** = (CÁCH GOM khách tại điểm vào — *entry key / axis*) × (METRIC theo dõi theo thời gian — *M+n*).
Cohort "first-order month" hiện có (dashboard #105) chỉ là **1 axis trong nhiều axis**. Khung này mở cả 2 trục: nhiều cách gom (axis) + nhiều metric.

- **Entry point** = đơn hàng ĐẦU TIÊN của khách (first order). Mọi entry-key (product/category/channel/basket/value) đều chốt tại đơn đầu, KHÔNG đổi về sau.
- **Cohort_size** = số khách trong nhóm, **cố định tại điểm vào** (mẫu số). Retention M+n = active_M+n / cohort_size. Cohort_size KHÔNG phải số active mỗi kỳ.
- **Min cohort size = 10:** nhóm <10 khách bị **ẩn** (cardinality vỡ vụn — chỉ ~1.515 khách lẻ có sale).

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Cohort Framework | Tệp khách vào bằng cách nào thì giữ chân/đẻ ra value tốt nhất? | Cohort Retention %, Revenue Retention, Repeat Rate (per axis) | `fact_orders`, `fact_sales`, `dim_customers` (entry-key derivable) | `int_customer_entry_attributes`, `mart_cohort_retention` (P2) |

### Analytical Questions

#### Q1. Cohort Framework Readiness

- **Question:** Tệp khách vào bằng cách nào (sản phẩm/kênh/giỏ/giá trị đầu) thì giữ chân và sinh value tốt nhất?
- **Definition:** Xác định axis nào tách được nhóm "vào rồi ở lại" khỏi nhóm "one-timer", để dồn acquisition/retention vào đúng entry path.
- **Nature:** retention + acquisition-quality, strategic/actionable.
- **Why It Matters:** 71.8% khách lẻ chỉ mua 1 lần, M+1 chỉ 3–17% (xem retention-leak §2.3). Cohort 1 chiều (acquisition month) chỉ cho thấy *có* xô thủng; cohort đa chiều chỉ ra *entry path nào* xô thủng nặng → can thiệp đúng chỗ.
- **Tradeoffs / Caveats:** Composite axis dễ vỡ cardinality → áp min-size=10, chỉ 2 composite duyệt trước. Relative vs calendar window đo 2 thứ khác nhau, không trộn.
- **Insight / Action Enabled:** Entry path retention cao → ưu tiên acquisition vào path đó; path retention thấp → fix onboarding/2nd-order hoặc ngừng đổ tiền acquisition vào đó.
- **Related Metrics:** Cohort Retention %, Revenue Retention, Repeat Rate (theo từng axis).

### Cohort Axes (entry key — cách gom v1)

Mỗi axis = `cohort_dimension`; giá trị nhóm = `cohort_value`. Tất cả chốt tại đơn đầu.

| cohort_dimension | cohort_value (ví dụ) | Định nghĩa entry-key | Nguồn |
|---|---|---|---|
| `first_order_month` | `2026-01` | Tháng mua đầu (DATE_TRUNC month của first_order_date) — **đã có**, port qua | `dim_customers.first_order_date` |
| `entry_product` | `Cordyceps 60v` | SKU của dòng đầu tiên trên đơn đầu | `fact_sales` (order-line grain) |
| `entry_category` | `Đông trùng` | Category của entry product | `fact_sales` × `dim_products.category` |
| `acquisition_channel` | `Shopee` | Kênh của đơn đầu | `fact_orders.channel_key` |
| `basket_size` | `1` / `≥2` | Số SKU phân biệt trên đơn đầu, band hoá 1 vs ≥2 | `fact_sales` (COUNT DISTINCT product per first order) |
| `entry_value_band` | `Bronze` / `Silver` / … | Band giá trị đơn đầu (first-order AOV band) | `fact_orders` (first order total) |

**Composite (v1 = 2 combo DUYỆT TRƯỚC, min size ≥10):**

| cohort_dimension | Ý nghĩa | Câu hỏi |
|---|---|---|
| `entry_product × acquisition_channel` | gateway SKU × kênh | Vào bằng X qua Shopee vs qua Web → retention/LTV khác nhau? |
| `basket_size × entry_value_band` | đơn đầu nhiều SKU × giá trị | Đơn đầu ≥2 SKU + giá trị cao → repeat rate cao hơn? |

> ⚠️ **Composite mới** ngoài 2 combo trên = **ĐỀ XUẤT**, phải duyệt trước khi thêm (tránh vỡ cardinality). KHÔNG sinh composite ad-hoc trong Metabase.

### Window Types (CẢ HAI)

| window_type | Trục thời gian | Dùng để |
|---|---|---|
| `relative` (primary) | `period_n` = M0, M1, M2… (tuổi cohort tính từ đơn đầu) | Cohort triangle — so sánh chéo cohort theo "tháng thứ n sau khi vào" |
| `calendar` | `period_n` = tháng lịch thực (wall-clock) | Xem mùa vụ / sự kiện ảnh hưởng cùng lúc lên mọi cohort |

### Metrics (theo dõi theo period_n)

| Metric | Định nghĩa | Logic | v |
|---|---|---|---|
| `retention_pct` | % khách cohort active ở period_n | `active_at_n / cohort_size * 100` | **v1** |
| `revenue_retention` | doanh thu period_n / doanh thu M0 của cohort | `rev_at_n / rev_at_M0` | **v1** |
| `repeat_rate` | % khách cohort có ≥2 đơn tính tới period_n | `customers_with_2plus_orders / cohort_size` | **v1** |
| `realized_margin` (per cohort) | margin theo cohort — **dùng `realized_margin_pct`, KHÔNG `gross_margin_pct`** (L125) | từ `mart_sku_economics_monthly` | v2 (ĐỀ XUẤT) |
| basket-expansion / cross-category | SKU/đơn tăng theo time; adoption dòng khác | từ `fact_sales` | v2 (ĐỀ XUẤT) |

### Architecture (long-format — Planned P2)

`mart_cohort_retention` = **1 bảng cho mọi axis** (long-format): build từ `int_customer_entry_attributes` (1 dòng/khách, mọi entry-key) + **1 CTE `activity` tính 1 lần** + UNION ALL mỗi axis (chỉ đổi `cohort_value`). Metabase filter `cohort_dimension` + `window_type` → ra ma trận tương ứng. **KHÔNG re-derive** metric đã pre-computed (L122).

```
mart_cohort_retention columns:
  cohort_dimension   -- axis name (first_order_month | entry_product | … | composite)
  cohort_value       -- nhóm cụ thể
  window_type        -- 'relative' | 'calendar'
  period_n           -- M0/M1/M2… (relative) hoặc tháng lịch (calendar)
  cohort_size        -- mẫu số, cố định tại entry (chỉ ghi nhóm ≥10)
  active             -- số khách active ở period_n
  retention_pct, revenue_retention, repeat_rate
```

### Common Misunderstandings

| Hiểu sai | Đúng | Hậu quả nếu nhầm |
|---|---|---|
| `cohort_size` = số khách active mỗi kỳ | `cohort_size` cố định tại điểm vào (mẫu số); `active` mới biến thiên | Retention% sai (chia nhầm mẫu số) |
| Sum `cohort_size` các nhóm hiển thị = tổng khách | Nhóm <10 bị ẩn → tổng visible < tổng base thật | Báo cáo thiếu khách, % sai lệch |
| `entry_product` = product_affinity | entry_product = SKU **đơn đầu**; `dim_customers.product_affinity` = SKU mua **nhiều nhất** | Gom nhầm nhóm, sai insight gateway |
| Relative M+n trộn được với calendar month | 2 window_type đo 2 thứ khác; lọc 1 trong 2, không cộng chéo | Cohort triangle vô nghĩa |
| Margin cohort dùng `gross_margin_pct` | Dùng `realized_margin_pct` (L125 — gross_* chưa fix H010) | Margin ~2× thấp ở SKU H010 |
| Composite axis thêm tuỳ ý trong BI | Chỉ 2 composite duyệt trước; min-size=10 | Cardinality vỡ, mỗi cell vài khách → noise |

## Context: Segmentation

> **Description:** Grouping customers by behavior.

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Segmentation | Which customer groups should be prioritized for care, retention, or reactivation? | 7. RFM Segment, 8. P3 Behavioral Metrics | See metric-level dbt sources | None documented |

### Analytical Questions

#### Q1. Segmentation Readiness

- **Question:** Which customer groups should be prioritized for care, retention, or reactivation?
- **Definition:** This question defines whether `Segmentation` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** segmentation, strategic/actionable.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 7. RFM Segment, 8. P3 Behavioral Metrics (discount_sensitivity, next_purchase_signal)

### Metrics

#### 7. RFM Segment

> **Phase 1 Status:** Ready (Rule-Based)
> **Phase 2 Status:** Planned (Statistics-Based NTILE)
##### Phase 1: Rule-Based Segmentation (Operational)

> **dbt Model:** [dim_customers](../../../transformation/models/marts/core/dim_customers.sql) - `value_group`, `customer_status`

- **Business Definition:** Fixed threshold segmentation for Operational consistency (Sales/CS).
- **Logic:**
  - **VALUE_VIP:** Lifetime Value >= 50,000,000 VND OR Total Orders >= 20
  - **VALUE_GOLD:** Lifetime Value >= 20,000,000 VND
  - **VALUE_SILVER:** Lifetime Value >= 5,000,000 VND
  - **VALUE_BRONZE:** Lifetime Value < 5,000,000 VND
  - **Active:** Last purchase <= 30 days
  - **At Risk:** Last purchase 31-90 days
  - **Churned:** Last purchase > 90 days

> **See:** [customer-segmentation.md](../../context/customer-segmentation.md) for full 8-dimension customer segmentation model.
##### Phase 2: Statistics-Based Segmentation (Analytical)

> **dbt Model:** Not yet implemented (Planned for Marketing Analysis)

- **Business Definition:** Relative segmentation using NTILE scoring (1-5) to identify top performers relative to the current period.
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
- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 8. P3 Behavioral Metrics

> **Phase 1 Status:** Ready (Implemented 2026-05-31)
> **dbt Model:** [int_customer_metrics](../../../transformation/models/marts/core/intermediate/int_customer_metrics.sql) (source) & [dim_customers](../../../transformation/models/marts/core/dim_customers.sql) (computed labels)

P3 Behavioral Metrics provide deeper insight into customer purchasing patterns and price sensitivity, enabling dynamic segmentation for targeted retention and reactivation campaigns.

##### 8.1 Average Order Spend (avg_order_spend)

- **Business Definition:** Average cash collected per non-cancelled, non-draft order — customer lens (VAT-inclusive).
- **Logic (SQL):**
  ```sql
  ROUND(SUM(total_collected) / NULLIF(COUNT(DISTINCT order_id), 0))::BIGINT
  WHERE status NOT IN ('CANCELLED', 'DRAFT')
  ```
- **Unit:** BIGINT (VND)
- **Grain:** Customer (one row per customer_key)
- **Scope:** All qualifying orders (excludes cancelled/draft)
- **Common Misunderstandings:** Uses `total_collected` (VAT-inclusive cash paid), not `net_revenue`. For period-level trend dashboards use `aov` (net_revenue / order_count) instead.
- **Pitfalls / Edge Cases:** NULL if customer has no non-cancelled orders; compare across same customer_type to avoid B2B distortion.

##### 8.2 Average Days Between Orders (avg_days_between_orders)

- **Business Definition:** Mean interval (in days) between consecutive non-cancelled, non-draft orders. Excludes same-day gaps to measure inter-visit cycle, not intra-day repeats.
- **Logic (SQL):**
  ```sql
  ROUND(AVG(date_diff('day', prev_order_date, order_date)))::INTEGER
  WHERE date_diff('day', prev_order_date, order_date) > 0
  ```
- **Unit:** INTEGER (days)
- **Grain:** Customer (one row per customer_key)
- **Scope:** Only gaps > 0 days (excludes same-day orders)
- **NULL Condition:** Returned for 1-time buyers (no prior order to measure gap)
- **Common Misunderstandings:** Measures inter-visit cycle (time between purchases), not calendar days; 0-day gaps excluded by design.
- **Pitfalls / Edge Cases:** NULL for single-order customers; used in predictive_next_purchase_date calculation (see 8.5).

##### 8.3 Discount Order Rate (discount_order_rate)

- **Business Definition:** Share of non-cancelled, non-draft orders where discount_amount > 0. Range [0.0–1.0] or NULL.
- **Logic (SQL):**
  ```sql
  COUNT(DISTINCT order_id) FILTER (WHERE discount_amount > 0)
    / NULLIF(COUNT(DISTINCT order_id), 0)
  WHERE status NOT IN ('CANCELLED', 'DRAFT')
  ```
- **Unit:** DOUBLE (0.0–1.0, stored as decimal)
- **Grain:** Customer (one row per customer_key)
- **Scope:** Qualifying (non-cancelled/draft) orders only
- **NULL Condition:** Returned when customer has 0 qualifying orders (distinct from 0.0 = never used discount)
- **Common Misunderstandings:** NULL ≠ 0; NULL means "no data to evaluate", 0.0 means "evaluated, never discounted".
- **Pitfalls / Edge Cases:** Sensitive to discount application logic; verify discount_amount definition aligns with business rules.

##### 8.4 Cancel Rate (cancel_rate)

- **Business Definition:** Share of attempted orders (excluding drafts) that were cancelled. Range [0.0–1.0].
- **Logic (SQL):**
  ```sql
  COUNT(DISTINCT order_id) FILTER (WHERE status = 'CANCELLED')
    / NULLIF(COUNT(DISTINCT order_id), 0)
  WHERE status != 'DRAFT'
  ```
- **Unit:** DOUBLE (0.0–1.0, stored as decimal)
- **Grain:** Customer (one row per customer_key)
- **Scope:** Attempted orders (all non-draft statuses)
- **NULL Condition:** Defaulted to 0.0 in dim_customers if customer has no cancellations
- **Common Misunderstandings:** Measures order-level cancellation, not item-level; draft orders excluded by design.
- **Pitfalls / Edge Cases:** High cancel_rate may indicate payment issues, regret, or system problems; investigate root cause per customer segment.

##### 8.5 Predicted Next Purchase Date (predicted_next_purchase_date)

- **Business Definition:** Estimated next purchase date = `last_order_date + avg_days_between_orders`. NULL for 1-time buyers or when avg_days_between_orders is uncomputed.
- **Logic (SQL):**
  ```sql
  CASE
      WHEN avg_days_between_orders IS NOT NULL AND frequency > 1
      THEN CAST(last_order_date AS DATE) + make_interval(days := avg_days_between_orders)
      ELSE NULL
  END
  ```
- **Unit:** DATE
- **Grain:** Customer (one row per customer_key)
- **Scope:** Repeat customers only (frequency > 1)
- **NULL Condition:** Returned for new/1-time buyers (no pattern yet)
- **Common Misunderstandings:** Predictive estimate, not a guarantee; based on historical average, assumes stable purchase rhythm.
- **Pitfalls / Edge Cases:** May be inaccurate for highly seasonal customers; always pair with next_purchase_signal (see 8.6) for context.

##### 8.6 Discount Sensitivity (discount_sensitivity) — Computed Label

- **Business Definition:** Purchase dependency on promotions; computed from discount_order_rate thresholds.
- **Values & Logic:**
  | Value | Condition | Business Meaning |
  |-------|-----------|------------------|
  | `PROMO_DEPENDENT` | discount_order_rate > 0.7 (70%+) | Customer highly likely to discount-hunt; priority for early promotion campaigns |
  | `PROMO_MIXED` | 0.3 < discount_order_rate ≤ 0.7 | Balanced purchase pattern; can convert with targeted promos |
  | `FULL_PRICE` | discount_order_rate ≤ 0.3 (≤30%) | Low discount dependency; driven by quality/trust, price-insensitive |
  | NULL | discount_order_rate IS NULL | No qualifying orders to evaluate |
- **SQL (in dim_customers):**
  ```sql
  CASE
      WHEN discount_order_rate IS NULL THEN NULL
      WHEN discount_order_rate > 0.7 THEN 'PROMO_DEPENDENT'
      WHEN discount_order_rate > 0.3 THEN 'PROMO_MIXED'
      ELSE 'FULL_PRICE'
  END AS discount_sensitivity
  ```
- **Common Use Cases:** Segment email campaigns by sensitivity; allocate discount budget to PROMO_MIXED cohort (highest ROI); protect FULL_PRICE from margin erosion.
- **Pitfalls / Edge Cases:** May flip seasonally (holiday spending patterns); review quarterly and pair with recent RFM status.

##### 8.7 Next Purchase Signal (next_purchase_signal) — Computed Label

- **Business Definition:** Lifecycle position relative to customer's own purchase rhythm; enables proactive engagement timing.
- **Values & Logic:**
  | Value | Condition | Business Meaning |
  |-------|-----------|------------------|
  | `OVERDUE` | recency_days ≥ avg_days_between_orders × 1.5 | Customer is 50%+ late; high reactivation priority |
  | `DUE_SOON` | recency_days ≥ avg_days_between_orders × 0.8 | Expected purchase window approaching (next ~5-14 days); timing-sensitive offer window |
  | `ON_TRACK` | recency_days < avg_days_between_orders × 0.8 | Within typical cycle; normal engagement cadence |
  | NULL | avg_days_between_orders IS NULL or frequency ≤ 1 | 1-time buyer (no pattern); use lifecycle_stage instead |
- **SQL (in dim_customers):**
  ```sql
  CASE
      WHEN avg_days_between_orders IS NULL OR frequency <= 1 THEN NULL
      WHEN recency_days >= avg_days_between_orders * 1.5 THEN 'OVERDUE'
      WHEN recency_days >= avg_days_between_orders * 0.8 THEN 'DUE_SOON'
      ELSE 'ON_TRACK'
  END AS next_purchase_signal
  ```
- **Common Use Cases:** Trigger "we miss you" campaign for OVERDUE segment; send product recommendations to DUE_SOON cohort; exclude ON_TRACK from re-engagement (avoid fatigue).
- **Pitfalls / Edge Cases:** NULL for 1-time buyers; recency drift if product is seasonal (manually adjust thresholds for seasonal verticals).

##### 8.8 SKU-Level Product Affinity — last/top/second

> **Phase 1 Status:** Ready (Implemented 2026-06-13)
> **dbt Model:** [int_customer_metrics](../../../transformation/models/marts/core/intermediate/int_customer_metrics.sql) (source) & [dim_customers](../../../transformation/models/marts/core/dim_customers.sql) (5 columns)
> **Also in:** [mart_customer_action_queue](../../../transformation/models/marts/customer/mart_customer_action_queue.sql)

Five columns provide SKU-level purchase preference signals for personalizing CSKH/Sales reorder and cross-sell scripts.

| Column | Type | Meaning |
|---|---|---|
| `last_purchased_product` | VARCHAR | Display name of SKU from customer's most-recent **paid** order; multi-SKU order → highest quantity line |
| `last_purchased_sku` | VARCHAR | SKU code of `last_purchased_product` |
| `top_affinity_product` | VARCHAR | SKU bought across the most distinct orders (repurchase frequency rank #1) |
| `top_affinity_sku` | VARCHAR | SKU code of `top_affinity_product` |
| `second_affinity_product` | VARCHAR | Frequency rank #2 SKU — for cross-sell. NULL if customer ever bought only 1 distinct paid SKU |

**Filter criteria (all three signals):** Only `net_revenue > 0` lines (excludes 0đ gift/swag — 43.9% of all order lines) on non-cancelled orders (`is_active_order`) with a non-NULL `product_name`. See [revenue_terminology.md](../guides/revenue_terminology.md) §7 for what `net_revenue = 0` means.

**Ranking key** for top/second affinity per `(customer, product)`: `COUNT(DISTINCT order_id) DESC → SUM(quantity) DESC → MAX(ordered_at) DESC → SUM(net_revenue) DESC → product_key ASC`.

**NULL meaning:** all three product columns NULL = customer has **never made a paid purchase** (only ever received gifts, e.g. CrossBorder/US gift recipients). These customers belong to a gift-conversion play, not a reorder script — do not confuse with "data missing".

**Display name:** `variant_name` when it differs from `product_name` (adds packaging info like "- Hộp"/"- Chai"); otherwise `product_name`.

**Relationship to brand-level `product_affinity`:** `product_affinity` is a brand label (4 values: `PRODUCT_FINE_JAPAN`, `PRODUCT_FG_CARE`, `PRODUCT_FINE_CARE`, `PRODUCT_MULTI`) derived from revenue share across brands. The SKU-level columns here are finer-grained and use **order frequency** (not revenue share) as the primary ranking signal. Use `product_affinity` for brand portfolio analysis; use the SKU columns for script personalization.

**Script use-cases:**

```
Reorder: "Lần trước anh/chị mua [last_purchased_product] (mã [last_purchased_sku]).
          Anh/chị có muốn bổ sung thêm không?"

Cross-sell: "Nhiều khách hay dùng [top_affinity_product] cùng với [second_affinity_product].
             Anh/chị đã thử [second_affinity_product] chưa?"
```

- **Common Misunderstandings:** `top_affinity_product` ≠ `last_purchased_product` for repeat buyers — the habitual item and the most-recent item often differ. Use both together for richer script context.
- **Pitfalls / Edge Cases:** NULL `second_affinity_product` is expected for customers who have purchased only one distinct SKU — do not substitute `top_affinity_product` as a fallback for cross-sell (they're the same item).

## Implementation Planning

#### 1. Deployment Strategy

- **Phase 1 (Immediate):** Deploy **"Operational Customer Dashboard"**.
  - **Audience:** Customer Success & Sales Operations.
  - **Key Features:** Customer Profile (Demographics), Retention & Churn (Historical), Value Group Segmentation (VALUE_VIP/GOLD/SILVER/BRONZE).
  - **Goal:** Enable daily operational decision-making (e.g., who to call today, who is at risk).

- **Phase 2 (Quarterly Review):** Deploy **"Strategic Customer Insights"**.
  - **Audience:** CMO & Head of Sales.
  - **Key Features:** CLV Projections, Market Segmentation (NTILE), CAC & ROI Analysis.
  - **Prerequisite:** Completion of `fact_marketing_spend` and predictive modeling dbt implementation.
#### 2. Preparation Checklist

- [x] **Dbt Models:** `dim_customers` and `fact_orders` are built and verified.
- [x] **Data Freshness:** Pipeline runs daily (ensuring `recency_days` is accurate).
- [x] **P3 Behavioral Metrics:** `int_customer_metrics` and `dim_customers` P3 columns implemented (2026-05-31).
- [ ] **Permissions:** Ensure Marketing & CS teams have "Collection View" access to "Customer Analytics" collection.
- [ ] **Marketing Data:** Accelerate the implementation of `fact_marketing_spend` (Required for CAC).
#### 3. Execution Steps

1.  **BI Tool Configuration:**
    - Create Collection: `Customer Analytics`.
    - Verify `dim_customers` metadata in Admin Panel (formatting currency for LTV, hiding PII if necessary).

2.  **Dashboard Development (Phase 1):**
    - **Report 1: Customer Overview:** Total Users, Active Users (MAU), New Users Trend.
    - **Report 2: Retention Watch:** Cohort Retention Heatmap, Churn Rate Trend.
    - **Report 3: Segment Performance:** Revenue by Value Group (VALUE_VIP/GOLD/SILVER/BRONZE), Order Frequency by Segment.

3.  **Training & Handover:**
    - **CS Team:** Training on interpreting "At Risk" vs "Churned" statuses for reactivation campaigns.
    - **Sales Team:** Understanding "VALUE_VIP" threshold requirements for loyalty program application.

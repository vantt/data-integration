# Customer Support Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** Customer Support Lead / Sales Ops
> **Update Frequency:** Real-time / Daily

## Context: Social Commerce Performance

> **Description:** Tracking the effectiveness of the CS team in converting social media inquiries (Facebook, Zalo) into orders.
> **dbt Source:** `fact_orders`

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Social Commerce Performance | Do social channels convert conversations into revenue and orders effectively? | 1. Social Sales Volume, 2. Social Order Count | `fact_orders` | None documented |

### Analytical Questions

#### Q1. Social Commerce Performance Readiness

- **Question:** Do social channels convert conversations into revenue and orders effectively?
- **Definition:** This question defines whether `Social Commerce Performance` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** social commerce, sales conversion.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 1. Social Sales Volume, 2. Social Order Count

### Metrics

#### 1. Social Sales Volume

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** GMV generated specifically from Social Media channels (Facebook, Zalo).
- **Logic (SQL):**
  ```sql
  SELECT
      channel_format,
      channel_name,
      SUM(gmv)
  FROM fact_orders
  LEFT JOIN dim_channels USING (channel_key)
  WHERE channel_format = 'Social'
  GROUP BY 1, 2
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** VND
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2. Social Order Count

> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

- **Business Definition:** Number of successful orders originating from social channels.
- **Logic (SQL):**
  ```sql
  SELECT COUNT(DISTINCT order_id)
  FROM fact_orders
  LEFT JOIN dim_channels USING (channel_key)
  WHERE channel_format = 'Social'
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** count
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Context: Support Efficiency (Planned)

> **Description:** Metrics related to response speed and ticket handling.
> **Status:** 🚧 Requirements Definition Only. Data not yet available in Warehouse.

> **Grain:** See metric-level grain notes

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Support Efficiency (Planned) | How quickly does the support team respond to and resolve conversations? | 3. First Response Time (FRT), 4. Average Handling Time (AHT) | See metric-level dbt sources | Source/model implementation required for planned metrics |

### Analytical Questions

#### Q1. Support Efficiency (Planned) Readiness

- **Question:** How quickly does the support team respond to and resolve conversations?
- **Definition:** This question defines whether `Support Efficiency (Planned)` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** support operations, service quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 3. First Response Time (FRT), 4. Average Handling Time (AHT)

### Metrics

#### 3. First Response Time (FRT)

> **Status:** 🔴 Missing Data

- **Requirement:** Time difference between _Customer First Message_ and _Agent First Reply_.
- **Target Grain:** Per Conversation.
- **Goal:** < 5 Minutes.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** hours/days
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 4. Average Handling Time (AHT)

> **Status:** 🔴 Missing Data

- **Requirement:** Average duration of a support conversation from open to close.
- **Target Grain:** Per Ticket/Conversation.

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** Planned / defined by the source model when implemented.
- **Unit:** hours/days
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

## Related Playbooks

| Playbook                                                                           | Description                                                      |
| :--------------------------------------------------------------------------------- | :--------------------------------------------------------------- |
| **[Social Commerce Operations](../playbooks/customer_support_social_commerce.md)** | Daily guide for CS Leads to monitor "Chat-to-Order" performance. |

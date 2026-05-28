# [Domain Name] Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** [Team Name, e.g., Sales Team]
> **Update Frequency:** [e.g., Daily, Weekly]

## Context: [Context Name]

> **Description:** [Mô tả ngắn — khi nào dùng metrics trong context này]
> **dbt Source:** `[dbt_model_name]` (e.g., `marts.sales.fact_orders`)
> **Grain:** [e.g., Per Order / Per Customer / Per Day]

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| [e.g., Revenue Quality] | [Question 1; Question 2] | [Metric A], [Metric B] | [Available model/field/table] | [Missing field/model/business input] |
| [e.g., Customer Behavior] | [Question 3] | [Metric C] | [Available model/field/table] | [None / planned source] |

### Analytical Questions

#### Q1. [Question Name]

- **Question:** [Câu hỏi phân tích nền tảng cần trả lời]
- **Definition:** [Câu hỏi này đo/quan sát điều gì trong nghiệp vụ]
- **Nature:** [Bản chất của vấn đề: leading/lagging, volume/value/quality, operational/strategic, etc.]
- **Why It Matters:** [Vì sao câu hỏi này quan trọng với business decision]
- **Tradeoffs / Caveats:** [Lợi hại, giới hạn, khi nào dễ đọc sai]
- **Insight / Action Enabled:** [Khi câu trả lời tăng/giảm/bất thường thì hành động gì, ai cần làm]
- **Related Metrics:** [Metric A], [Metric B]

#### Q2. [Question Name]

- **Question:** [...]
- **Definition:** [...]
- **Nature:** [...]
- **Why It Matters:** [...]
- **Tradeoffs / Caveats:** [...]
- **Insight / Action Enabled:** [...]
- **Related Metrics:** [...]

### Metrics

#### 1. [Metric Name]

> **Status:** `active`
> **dbt Model:** [`model_name`](../../transformation/models/path/to/model.sql)

- **Business Definition:** [Định nghĩa sâu về nghiệp vụ: metric đại diện cho điều gì, phạm vi nào được tính, điều kiện loại trừ, và tại sao business nên tin cách đo này]
- **Business Logic:** [Logic tính toán bằng ngôn ngữ nghiệp vụ trước khi viết SQL; nêu numerator/denominator, grain, filter, dedup, time basis nếu có]
- **Formula:** [Công thức business/math ngắn gọn, e.g., Net Revenue = Gross Revenue - Discounts]
- **Logic (SQL):**
  ```sql
  -- Công thức tính
  SUM(amount - discount)
  ```
- **Unit:** [VND / % / count / ...]
- **Classification:** [leading / lagging] | [absolute / relative]
- **Related Metrics:** [Nếu có quan hệ: "Derived from Gross Revenue minus Discounts"]
- **Common Misunderstandings:** [Hiểu lầm/sai lầm thường gặp, ví dụ nhầm gross vs net, tính cả đơn hủy, sai grain, sai thời gian]
- **Pitfalls / Edge Cases:** [Các trường hợp dễ làm sai khi query/report]

#### 2. [Metric Name]

> **Status:** `active`
> **dbt Model:** [`model_name`](path)

- **Business Definition:** [...]
- **Business Logic:** [...]
- **Formula:** [...]
- **Logic (SQL):**
  ```sql
  [expression]
  ```
- **Unit:** [...]
- **Common Misunderstandings:** [...]
- **Pitfalls / Edge Cases:** [...]

<!-- Thêm metrics theo cùng format -->

---

## Available Dashboards

| Dashboard | Audience | Purpose | Blueprint |
|-----------|----------|---------|-----------|
| [Dashboard Name] | [Role] | [1-line purpose] | [`blueprint`](../blueprints/name.md) |

## Related Playbooks

| Playbook | Uses Metrics |
|----------|-------------|
| [Playbook Name](../playbooks/name.md) | Metric 1, Metric 2 |

<!--
Metric Status Reference:
  - `active`     — dbt model exists, data available, ready to query
  - `planned`    — metric defined but dbt model not yet built
  - `deprecated` — no longer used, kept for historical reference
-->

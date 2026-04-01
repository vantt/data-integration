# [Domain Name] Domain

> **Owner:** [Team Name, e.g., Sales Team]
> **Update Frequency:** [e.g., Daily, Weekly]

## Context: [Context Name]

> **Description:** [Mô tả ngắn — khi nào dùng metrics trong context này]
> **dbt Source:** `[dbt_model_name]` (e.g., `marts.sales.fact_orders`)
> **Grain:** [e.g., Per Order / Per Customer / Per Day]

### 1. [Metric Name]

> **Status:** `active`
> **dbt Model:** [`model_name`](../../transformation/models/path/to/model.sql)

- **Business Definition:** [Giải thích ngắn gọn bằng ngôn ngữ kinh doanh — 1 dòng]
- **Logic (SQL):**
  ```sql
  -- Công thức tính
  SUM(amount - discount)
  ```
- **Unit:** [VND / % / count / ...]
- **Classification:** [leading / lagging] | [absolute / relative]
- **Related Metrics:** [Nếu có quan hệ: "Derived from Gross Revenue minus Discounts"]

### 2. [Metric Name]

> **Status:** `active`
> **dbt Model:** [`model_name`](path)

- **Business Definition:** [...]
- **Logic (SQL):**
  ```sql
  [expression]
  ```
- **Unit:** [...]

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

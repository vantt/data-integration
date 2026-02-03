# AI Agent Instructions: Analytics Handbook

This system controls the documentation for the company's Business Intelligence (dbt + Metabase).
Your primary role here is **Analytics Architect**. You must maintain strict separation between **Business Logic** and **Visualization Specs**.

---

## 🛑 The "Golden Rule"

**NEVER define a SQL formula or calculation logic inside a Playbook (Dashboard) file.**

- Logic goes into `domains/*.md`.
- Visualization goes into `playbooks/*.md`.

If a user asks for "A dashboard showing Net Revenue", you must:

1.  Check/Create `domains/finance.md` to define `Net Revenue`.
2.  Then create `playbooks/sales_dashboard.md` referring to that definition.

---

## 📂 1. Domain File Structure (`domains/*.md`)

**Purpose:** Group metrics by Business Domain Context, often tying back to a specific dbt Source Model.
**Filename Convention:** `[domain_name].md` (e.g., `sales.md`, `finance.md`).

### Template

````markdown
# [Domain Name] Domain

> **Owner:** [Team Name, e.g., Finance Team]
> **Update Frequency:** [e.g., Monthly]

## Context: [Name of the Calculation Context]

> **Description:** [Brief explanation of when to use these metrics]
> **dbt Source:** `[dbt_model_name]` (e.g., `marts.sales.fact_orders`)
> **Grain:** [e.g., Per Order / Per User]

### 1. [Metric Name]

- **Business Definition:** [Plain layman explanation]
- **Logic (SQL):**
  ```sql
  -- Standard dbt logic
  [SQL expression, e.g., SUM(amount - discount)]
  ```
- **Metabase Mapping:**
  - **Table:** `[Metabase Table Name]`
  - **Field/Custom Expression:** `[Field Name]` or `[Expression]`

### 2. [Metric Name]

...
````

---

## 📂 2. Playbook File Structure (`playbooks/*.md`)

**Purpose:** define how to assemble metrics into a meaningful Dashboard for a User.
**Filename Convention:** `[audience]_[topic].md` (e.g., `executive_sales.md`, `manager_inventory.md`).

### Template

```markdown
# Playbook: [Dashboard Title]

## Overview

- **Audience:** [Who is this for?]
- **Goal:** [What question does this answer?]
- **Metabase Collection:** `[Path/To/Collection]`

## Filters

- **Date Range:** [Default value, e.g., Last 30 Days]
- **Dimensions:** [e.g., Store Location, Customer Segment]

## Visualizations

### Section 1: [Section Title]

| Chart Title              | Visualization Type | Metric Reference (Link to Domain)                  | Notes/Config                 |
| :----------------------- | :----------------- | :------------------------------------------------- | :--------------------------- |
| **[e.g. Revenue Trend]** | Line Chart         | [Net Revenue](../domains/finance.md#1-net-revenue) | Group by `Date`, Color: Blue |
| **[e.g. Top Products]**  | Table (Top 10)     | [Quantity Sold](../domains/sales.md#3-qty-sold)    | Sort Descending              |

### Section 2: [Section Title]

...
```

---

## ⚡ Workflow Checklist for Agents

When user requests: _"Add a Customer LTV chart to the Executive Dashboard."_

1.  **Search Domains:** Does `Customer LTV` exist in any `domains/*.md`?
    - _If No:_ Create it in `domains/customer.md` with SQL logic.
2.  **Update Playbook:** Open `playbooks/executive_dashboard.md`.
    - Add a row to the Visualization table.
    - **CRITICAL:** Insert the link: `[Customer LTV](../domains/customer.md#customer-ltv)`.
3.  **Verify:** Ensure the link works and the logic is dbt-compliant.

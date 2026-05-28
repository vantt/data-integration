# AI Agent Instructions: Analytics Handbook

This system controls the documentation for the company's Business Intelligence (dbt + Metabase + Rill).
Your primary role here is **Analytics Architect**. You must maintain strict separation between **Business Logic** and **Visualization Specs**.

**Platforms:**
- **Metabase**: Operational dashboards, static reports (`blueprints/*.md`)
- **Rill**: Self-service exploration, semantic layer (`blueprints/rill/*.yaml`)

---

## 🛑 The "Golden Rule"

**NEVER define a SQL formula or calculation logic inside a Playbook (Dashboard) file.**

- Logic goes into `domains/*.md`.
- Visualization Story goes into `playbooks/*.md` (Human-readable "Why" & "What").
- Technical Implementation (SQL/JSON) goes into `blueprints/*.md` (Machine-executable "How").

If a user asks for "A dashboard showing Net Revenue", you must:

1.  Check/Create `domains/finance.md` to define `Net Revenue`.
2.  Then create `playbooks/sales_dashboard.md` referring to that definition.

---

## 📐 Naming Conventions

### File Naming

| Type | Pattern | Examples |
|:---|:---|:---|
| Domain | `[domain].md` | `sales.md`, `finance.md`, `customer_support.md` |
| Playbook | `[audience]_[cadence]_[topic].md` | `ceo_weekly_pulse.md`, `marketing_monthly_analysis.md`, `sales_ops_weekly_review.md` |
| Blueprint | Same as playbook | `ceo_weekly_pulse.md`, `sales_ops_monthly_summary.md` |

- Use `lowercase_with_underscores` for all file names.
- Playbook and its corresponding blueprint MUST have the **same filename** (in different directories).
- Audience prefix: `ceo_`, `marketing_`, `sales_ops_`, `sales_`, `customer_`.
- Cadence: `daily_`, `weekly_`, `monthly_` (omit if the dashboard has no fixed cadence).

### Dashboard Naming

- Dashboard name = human-readable title. Cadence is part of the name.
- Good: `CEO Weekly Pulse`, `Marketing Monthly Analysis`, `Sales Ops Weekly Review`
- Bad: `Weekly Report`, `Monthly Dashboard`, `New Dashboard`

### Question (Card) Naming

- Descriptive, standalone-readable. Include time scope if relevant.
- Good: `Revenue by Channel Category`, `Top 10 Products by Revenue`, `Cancellation Rate Trend (6M)`
- Bad: `Chart 1`, `Query`, `Revenue`

---

## 📂 1. Domain File Structure (`domains/*.md`)

**Purpose:** Group metrics by Business Domain Context, often tying back to a specific dbt Source Model.
**Filename Convention:** `[domain_name].md` (e.g., `sales.md`, `finance.md`).

**Required document definition:** Every new domain file MUST include the following block immediately after the H1 title:

```markdown
> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.
```

### Template

````markdown
# [Domain Name] Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

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

**Required document definition:** Every new playbook file MUST include the following block immediately after the H1 title:

```markdown
> **Tài liệu này mô tả mục đích và cách sử dụng dashboard/report từ góc nhìn người dùng nghiệp vụ.**
> Nó giải thích dashboard dành cho ai, dùng để trả lời câu hỏi nào, cần đọc theo luồng nào, dùng những metric nào từ domain documents, và khi thấy tín hiệu bất thường thì ai cần làm gì.
> Playbook không định nghĩa công thức tính metric; mọi logic nghiệp vụ phải được tham chiếu từ `domains/`.
```

### Template

```markdown
# Playbook: [Dashboard Title]

> **Tài liệu này mô tả mục đích và cách sử dụng dashboard/report từ góc nhìn người dùng nghiệp vụ.**
> Nó giải thích dashboard dành cho ai, dùng để trả lời câu hỏi nào, cần đọc theo luồng nào, dùng những metric nào từ domain documents, và khi thấy tín hiệu bất thường thì ai cần làm gì.
> Playbook không định nghĩa công thức tính metric; mọi logic nghiệp vụ phải được tham chiếu từ `domains/`.

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

## 📂 3. Blueprint File Structure (`blueprints/*.md`)

**Purpose:** Deployable technical specification — parsed by `deploy_from_markdown.js` to create Metabase resources automatically.
**Filename Convention:** Same as playbook (e.g., `ceo_weekly_pulse.md`).

### Template

````markdown
# 📘 Blueprint: [Dashboard Name]

**Playbook**: [Link to playbook](../playbooks/[same_name].md)

> **Target Collection:** `[Collection Path from registry]`
> **Role:** [Audience]
> **Archetype:** [Executive Pulse / Operational Cockpit / Exploratory Tool]

## 📂 Collection: [Parent] > [Child]

[One-line description of this collection.]

### 🧊 Model: [Model Name]   ← optional, only if dashboard needs a pre-aggregated model

[Description of what this model does.]

```sql
SELECT ... FROM ...
```

### 🖥️ Dashboard: [Dashboard Name]

**Description**: [One sentence explaining the dashboard purpose.]

#### ❓ Question: [Question Name]

[Optional description or domain reference link.]

**Domain Reference**: [Metric Name](../domains/[domain].md#[anchor])

```sql
SELECT ...
FROM fact_orders
WHERE status NOT IN ('CANCELLED', 'Voided')
  AND order_timestamp >= ...
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": { ... }
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```
````

### Blueprint Code Block Reference

| Block | Purpose | Required? |
|:---|:---|:---|
| `` ```sql `` | The SQL query for the question/model | **Yes** |
| `` ```json metabase-viz `` | Visualization settings (display type, colors, axes) | Recommended |
| `` ```json metabase-pos `` | Grid position on the dashboard (`row`, `col`, `size_x`, `size_y`) | Recommended |
| `` ```json metabase-model `` | Model column metadata (display names, semantic types) | Optional |
| `` ```sql --metric `` | Metric formula (for Metabase Metric layer) | Optional |

### Dashboard Grid System

- Grid width: **18 units**.
- Scalar KPIs: `size_x: 3–4`, `size_y: 3`. Place 4–6 across the top row.
- Charts (line, bar, pie): `size_x: 6–12`, `size_y: 6–8`.
- Tables: `size_x: 9–18`, `size_y: 6`.
- Rows increment by the height of the tallest card in that visual row.

---

---

## 🗄️ SQL Conventions for Blueprints

All SQL in blueprints targets **DuckDB** (via Metabase Native Query). Follow these rules:

### Filtering

```sql
-- ALWAYS exclude cancelled/voided orders for revenue metrics
WHERE status NOT IN ('CANCELLED', 'Voided')

-- Date ranges: use date_trunc + INTERVAL, never hardcoded dates
AND order_timestamp >= date_trunc('month', current_date) - INTERVAL '1 month'
AND order_timestamp < date_trunc('month', current_date)
```

### Date Functions (DuckDB syntax)

| Operation | DuckDB Syntax | ❌ NOT this |
|:---|:---|:---|
| Truncate to month | `date_trunc('month', ts)` | `DATE_FORMAT(ts, '%Y-%m-01')` |
| Date difference | `date_diff('day', start, end)` | `DATEDIFF(start, end)` |
| Extract part | `EXTRACT(HOUR FROM ts)` | `HOUR(ts)` |
| Format date | `strftime(ts, '%Y-%m-%d')` | `DATE_FORMAT(ts, ...)` |
| Interval | `INTERVAL '7 days'` | `INTERVAL 7 DAY` |
| Cast to date | `date(ts)` or `CAST(ts AS DATE)` | `DATE(ts)` (MySQL) |

### Joins & Keys

- All dimension joins use **surrogate keys** (MD5 hashes from `dbt_utils.generate_surrogate_key()`).
- Always use `LEFT JOIN` for dimensions to avoid losing fact rows when dimension is 'Unknown'.
- Example: `JOIN dim_channels c ON o.channel_key = c.channel_key`

### Comparisons (WoW, MoM)

Use CTE pattern — `this_period` vs `last_period`:

```sql
WITH this_week AS (
    SELECT ... WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
                 AND order_timestamp < date_trunc('week', current_date)
),
last_week AS (
    SELECT ... WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '14 days'
                 AND order_timestamp < date_trunc('week', current_date) - INTERVAL '7 days'
)
SELECT ..., ROUND((tw.value - lw.value) * 100.0 / NULLIF(lw.value, 0), 1) as "WoW %"
FROM this_week tw LEFT JOIN last_week lw ON ...
```

### Formatting

- Currency columns: `{ "number_style": "currency", "currency": "VND" }`
- Percent columns: `{ "suffix": "%", "decimals": 1 }` or `{ "number_style": "percent" }`
- Column aliases: Use `"Double Quoted"` for human-readable names in SELECT.
- Sort: Always add `ORDER BY` — revenue DESC for rankings, date ASC for trends.

### Safety

- Always use `NULLIF(denominator, 0)` to prevent division by zero.
- Use `COALESCE(nullable_field, 0)` for discount/tax amounts.
- `COUNT(DISTINCT order_id)` — not `COUNT(*)` — for order counts (avoid duplicate rows).

---

## 🛠️ Tools & Skills

### Metabase

To implement Blueprints, use the **Metabase Automation Skill**.

- **Skill Definition**: `.skills/metabase-automation/SKILL.md`
- **Capability**: Programmatically create Collections, Questions (Cards), and Dashboards from JSON/Markdown specs.

#### Available Workflows

Use these slash commands to accelerate your work:

- **/create_metabase_blueprint**: Generates a new Blueprint file from a template.
- **/deploy_metabase_blueprint**: Deploys a specific Blueprint file to the Metabase instance.
  - *Usage*: `node .skills/metabase-automation/scripts/deploy_blueprint.js [path/to/blueprint.md]`
- **/manage_metabase_resources**: General management (sync schemas, list collections).

### Rill

Rill uses YAML-based semantic layer definitions. Blueprints are in `blueprints/rill/*.yaml`.

#### Directory Structure

```
rill/
├── models/                     # Data sources & enriched models
│   ├── src_*.yaml              # Source connectors (parquet)
│   ├── orders_enriched.sql     # Enriched model with joins
│   └── sales_items_enriched.sql
├── metrics/                    # Metrics views (semantic layer)
│   ├── orders_core_metrics.yaml
│   └── sales_items_core_metrics.yaml
└── dashboards/                 # Explore configurations
    └── orders_core.yaml
```

#### Deployment

```bash
# Deploy from blueprint to Rill
cp docs/analytics-handbook/blueprints/rill/orders_executive.yaml rill/dashboards/
```

#### 3-Layer Scope Architecture

Rill metrics include scope flags for the 3-layer architecture:

| Scope | Filter | Layer |
|-------|--------|-------|
| `scope_sales` | `is_sales_channel AND not cancelled` | Executive [All] |
| `scope_retail` | `scope_sales AND customer_type='RETAIL'` | Retail [Retail] |
| `scope_b2b` | `scope_sales AND customer_type IN (WHOLESALE, PARTNER)` | B2B [B2B] |

Pre-filtered measures are available: `sales_revenue`, `retail_revenue`, `b2b_revenue`.

#### Rill Playbooks vs Metabase Playbooks

| Aspect | Metabase | Rill |
|--------|----------|------|
| Location | `playbooks/*.md` | `playbooks/rill/*.md` |
| Focus | Static dashboard layout | Explore configuration |
| Filters | Tab-based | Dimension-based |
| Deployment | `deploy_from_markdown.js` | Copy YAML to `rill/dashboards/` |

## 💡 Tips for Success

1.  **Start Small**: Begin with one domain and expand.
2.  **Naming Consistency**: Use `lowercase-with-hyphens` for all file names.
3.  **Document Everything**: Future agents will thank you.
4.  **Test Before Deploy**: Always verify SQL queries work in Metabase before creating a Blueprint.
5.  **Use Cross-References**: Link between related documents (e.g., `[Metric](../domains/sales.md#metric)`).

6.  **Maintain Traceability**: Ensure `Domain <--> Playbook <--> Blueprint` linkage is explicit.
    - **Blueprint -> Domain**: Every SQL query in a Blueprint must link back to its definition in a Domain file.
    - **Playbook -> Blueprint**: Every Playbook should link to its technical Blueprint if one exists.

---

## 📂 Collection Governance

### The Problem
Creating collections ad-hoc leads to a messy Metabase sidebar (orphan "Weekly Reports" that mixes CEO + Marketing + Ops dashboards). Users can't find their dashboards.

### The Rule
**ALWAYS read [`collection_registry.yml`](./collection_registry.yml) before creating a blueprint.** This file is the single source of truth for the Metabase collection hierarchy.

> **Why this structure?** See [`guides/collection_organization.md`](./guides/collection_organization.md) for the full rationale — organized by audience, not topic or cadence.

### Collection Architecture (3 Collections)

With a small team (~5 users) where people wear multiple hats, we use **3 top-level collections**, each answering one core question:

```
📁 Executive                          ← "Công ty đang thế nào?"
│   ├── CEO Weekly Pulse
│   ├── CEO Monthly Scorecard
│   └── Sales Executive Dashboard
│
📁 Marketing & Customers              ← "Kênh/Khách thế nào?"
│   ├── Marketing Weekly Tracker
│   ├── Marketing Monthly Analysis
│   ├── Customer Operational Dashboard
│   └── Customer Retention & Churn
│
📁 Operations                         ← "Hôm nay cần làm gì?"
│   ├── Daily Monitoring/
│   │   ├── Daily Sales, Yesterday's Sales
│   │   └── Today's Orders, Yesterday's Orders
│   ├── Periodic Reviews/
│   │   ├── Sales Ops Weekly Review
│   │   └── Sales Ops Monthly Summary
│   └── Social Commerce Operations
```

### Collection Placement Workflow

1. **Identify the audience** of the dashboard.
2. **Ask the decision question:**

   | Question | Collection Path |
   |:---|:---|
   | "Is this for **strategic oversight**?" (CEO, Board, Sales Director) | `Executive` |
   | "Is this for **channel/customer analysis**?" (Marketing, CS) | `Marketing & Customers` |
   | "Is this for **daily action items**?" (Store Manager, Ops) | `Operations > Daily Monitoring` |
   | "Is this for **weekly/monthly ops review**?" (Sales Ops, CS Lead) | `Operations > Periodic Reviews` |
   | "Is this for **social commerce**?" (CS Lead) | `Operations` |

3. **Use the path in the blueprint** with `>` syntax:
   ```markdown
   ## 📂 Collection: Operations > Periodic Reviews
   ```
   The deploy script will create "Operations" (if needed), then "Periodic Reviews" as a child.

4. **If no collection matches** the audience → update `collection_registry.yml` first, then create the blueprint. Never invent ad-hoc collection names.

### Key Principles
- **Organize by AUDIENCE** (who uses it), not by cadence (daily/weekly/monthly).
- **Cadence goes in the dashboard name**, not the collection name.
- **Max 2 levels deep**. No `A > B > C > D` nesting.
- **Collection names must be unique within the same parent.

### When to Split
- Team > 15 people with dedicated Customer Success → split `Marketing & Customers` into `Marketing` + `Customer Analytics`
- Sales Director ≠ CEO, needs separate permissions → split `Executive` into `Executive` + `Sales Analytics`
- Any collection exceeds ~8 dashboards → add sub-collections or new top-level

---

## 📂 4. Design Spec File Structure (`designs/*.md`) — NEW

**Purpose:** Tool-agnostic design specification — contract between Analytics Design (Phase 0-6) and Metabase Automation (Phase 7-10).
**Filename Convention:** Same as playbook/blueprint (e.g., `ceo_weekly_pulse.md`).
**Created by:** Analytics Design Skill (`.skills/analytics-design/`)

### Template

```yaml
---
title: [Dashboard Title]
archetype: [Executive Pulse / Operational Cockpit / Exploratory Tool]
status: [final / draft / draft-from-capture]
last_modified: YYYY-MM-DD
domain_refs: [domains/sales.md, domains/customer.md]
---
```

Sections: Brief, Constraints & Filters, Views, Composition (table with Role, Viz Type, Color tokens, Size tokens).

See full template: `.skills/analytics-design/templates/design_spec_template.md`

**Key traits:**
- Uses **YAML frontmatter** (unlike domains/playbooks which use blockquote metadata) — needed for staleness detection
- Uses **standard vocabulary** for viz types (not Metabase display types)
- Uses **semantic tokens** for colors and sizes (not hex codes or pixels)
- `status: draft-from-capture` marks reverse-generated specs that need analyst review

---

## 📋 Artifact Ownership

| Directory | Owned by | Skill knowledge |
|-----------|----------|-----------------|
| `domains/` | Analytics Design | `.skills/analytics-design/*` |
| `playbooks/` | Analytics Design | `.skills/analytics-design/*` |
| `guides/` | Analytics Design | `.skills/analytics-design/*` |
| `designs/` | Analytics Design | `.skills/analytics-design/*` |
| `blueprints/` | Metabase Automation | `.skills/metabase-automation/*` |

**Creation order**: domain → playbook → [guide] → design spec → blueprint → deploy

---

## ⚡ Workflow Checklist for Agents

When user requests: _"Add a Customer LTV chart to the Executive Dashboard."_

1.  **Search Domains:** Does `Customer LTV` exist in any `domains/*.md`?
    - _If No:_ Create it in `domains/customer.md` with SQL logic.
2.  **Update Playbook:** Open `playbooks/executive_dashboard.md`.
    - Add a row to the Visualization table.
    - **CRITICAL:** Insert the link: `[Customer LTV](../domains/customer.md#customer-ltv)`.
3.  **Update Design Spec:** Open `designs/executive_dashboard.md` (if exists).
    - Add new card to Composition table with role, viz type, color/size tokens.
    - Update `last_modified` in frontmatter.
4.  **Check Collection Registry:** Read `collection_registry.yml` to confirm the target collection path.
5.  **Create/Update Blueprint:** Translate Design Spec → blueprint using `METABASE_VIZ_CATALOG.md`.
6.  **Deploy (Optional):** Use `/deploy-metabase-blueprint` to push to Metabase.

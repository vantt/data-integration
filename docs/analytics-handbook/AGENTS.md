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

## Documentation Boundary: Data Model vs Analytics Domain

Analytics handbook documents do not own the full system data model.

| Need | Write it in |
|:---|:---|
| Business question, metric definition, formula, scope, caveats | `docs/analytics-handbook/domains/*.md` |
| Dashboard purpose, reading flow, action triggers | `docs/analytics-handbook/playbooks/*.md` |
| Tool-agnostic dashboard layout, card roles, visualization choices | `docs/analytics-handbook/designs/*.md` |
| Deployable BI SQL/configuration | `docs/analytics-handbook/blueprints/*.md` |
| Table inventory, grain, primary/foreign keys, fact/dimension relationships, ERD, planned analytical tables | `docs/architecture/data-model.md` |
| Column definitions, field meanings, data types, examples | `docs/architecture/data-dictionary.md` |
| Raw source payloads, nested structures, source natural keys, ingestion envelope | `docs/architecture/source-entities/<source>.md` |
| dbt source/model columns and tests | `transformation/models/**/schema.yml`, `transformation/models/sources.yml` |

If a domain metric needs a datasource that is not in dbt yet, mark the metric as `planned` in the domain and list the missing model/fields in `Needs Added`. Put the broader table relationship and grain in `docs/architecture/data-model.md`; put raw payload schema in `docs/architecture/source-entities/`; put column-level dictionary detail in `docs/architecture/data-dictionary.md`.

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

#### **Rule 6 — Scope Suffix is MANDATORY** ⚠️

Every dashboard name MUST end with a scope suffix in square brackets:

| Suffix | Meaning | Example |
|:---|:---|:---|
| `[All]` | All customer types (`scope_sales`) | `CEO Weekly Pulse [All]` |
| `[Retail]` | Retail customers only (`scope_retail`) | `Promotion Analysis [Retail]` |
| `[B2B]` | B2B/Wholesale customers only (`scope_b2b`) | `B2B Daily Sales [B2B]` |
| `[Cross]` | Cross-segment comparison | `Channel Profitability [Cross]` |
| `[US]` | US cross-border arrangements | `US CrossBorder Daily [US]` |
| `[Internal]` | Internal ops (e.g. recon, ingestion health) | `Accounting Reconciliation Cockpit [Internal]` |

**Where to apply the suffix:**
1. `dashboard_name:` in YAML frontmatter — `dashboard_name: Finance Services Revenue [All]`
2. Blueprint h1 title — `# 📘 Blueprint: Finance Services Revenue [All]`
3. Dashboard h3 — `### 🖥️ Dashboard: Finance Services Revenue [All]`
4. `collection_registry.yml` dashboards list — `- "Finance Services Revenue [All]"`

**All four must match.** Mismatch → deploy script creates a duplicate dashboard with the new name instead of updating the existing one (lesson learned 2026-05-28: had to manually archive `Finance Services Revenue` id 93 after rename to `Finance Services Revenue [All]` id 95).

**Why mandatory:** Same dashboard concept may exist for both [Retail] and [B2B] (e.g. `Daily Sales [Retail]` vs `B2B Daily Sales [B2B]`). The suffix prevents name collision and makes the audience explicit.

**Exception — system landing pages:** Onboarding/welcome dashboards that are NOT analytics (no SQL, no data scope, just navigation/docs) are exempt from the suffix requirement. Example: `Welcome to ChợPulse BI` (in `📍 Start Here` collection). These are routed to users via collection placement, not scope; adding a suffix would be misleading. All four places (live name, h1, h3, registry) must still match — exemption applies uniformly.

**Registry check:** When adding a new dashboard, update `collection_registry.yml` BEFORE first deploy. The registry entry must use the exact same name (with suffix) — drift triggers the daily Lark alert (`scripts/validate-collections.js`).

### Question (Card) Naming

- Descriptive, standalone-readable. Include time scope if relevant.
- Good: `Revenue by Channel Category`, `Top 10 Products by Revenue`, `Cancellation Rate Trend (6M)`
- Bad: `Chart 1`, `Query`, `Revenue`

---

## 📂 1. Domain File Structure (`domains/*.md`)

**Purpose:** Group metrics by Business Domain Context, often tying back to a specific dbt Source Model.
**Filename Convention:** `[domain_name].md` (e.g., `sales.md`, `finance.md`).

**Required context structure:** Every context MUST be written in this order:

1. `Context Overview` table: category, foundational analytical questions, related metrics, data ready, needs added.
2. `Analytical Questions`: for each question, define it, explain its nature, why it matters, tradeoffs/caveats, and insight/action enabled.
3. `Metrics`: after the questions are clear, define the metrics. `Business Definition` must be deep enough to explain business meaning, calculation logic, common misunderstandings, and common mistakes.

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

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
| :------- | :-------------------------------- | :-------------- | :--------- | :---------- |
| [Category] | [Question 1; Question 2] | [Metric A], [Metric B] | [Available model/field/table] | [Missing model/field/business input] |

### Analytical Questions

#### Q1. [Question Name]

- **Question:** [Foundational analytical question]
- **Definition:** [What this question observes in the business]
- **Nature:** [Nature of the issue: leading/lagging, volume/value/quality, operational/strategic]
- **Why It Matters:** [Why this question matters for decision-making]
- **Tradeoffs / Caveats:** [Benefits, limitations, and how it can be misread]
- **Insight / Action Enabled:** [Insight/action triggered by the answer]
- **Related Metrics:** [Metric A], [Metric B]

### Metrics

#### 1. [Metric Name]

- **Business Definition:** [Deep business definition: meaning, scope, exclusions, and why this measurement represents business reality]
- **Business Logic:** [Calculation logic in business language: grain, filters, numerator/denominator, dedup/time basis if relevant]
- **Formula:** [Short business/math formula, e.g., Net Revenue = Gross Revenue - Discounts]
- **Logic (SQL):**
  ```sql
  -- Standard dbt logic
  [SQL expression, e.g., SUM(amount - discount)]
  ```
- **Unit:** [VND / % / count / ...]
- **Common Misunderstandings:** [Common misconceptions or reporting mistakes]
- **Pitfalls / Edge Cases:** [Duplicate grain, canceled orders, missing timestamps, null handling, etc.]

#### 2. [Metric Name]

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
WHERE scope_retail
  AND is_active_order    -- revenue metric: exclude cancelled
  AND ordered_at >= ...
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

### Chu kỳ báo cáo — Bắt buộc ở đầu mỗi tab

**Quy tắc:** Mọi dashboard tab phải có 1 card hiển thị khoảng thời gian cụ thể ở `row: 0`. Người dùng phải thấy ngay "đang xem dữ liệu của tuần nào / tháng nào" mà không cần đọc tiêu đề.

**Cấu hình bắt buộc:**
```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```
```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

**Tại sao `size_y: 2`?** `size_y: 1` không đủ chiều cao — Metabase chỉ render card title, không render giá trị SQL. `card.title: ""` ẩn tên card. `dashcard.background: false` xóa viền và nền trắng → kết quả là chữ thuần, không có chrome.

**SQL theo cadence (DuckDB):**

| Cadence | SQL |
|:---|:---|
| Daily | `SELECT '📅 Hôm nay: ' \|\| strftime(current_date, '%d/%m/%Y') \|\| '  ·  Hôm qua: ' \|\| strftime(current_date - 1, '%d/%m/%Y') AS " "` |
| Weekly | `SELECT '📅 Tuần này: ' \|\| strftime(date_trunc('week', current_date), '%d/%m/%Y') \|\| ' → ' \|\| strftime(current_date, '%d/%m/%Y') \|\| '  ·  Tuần trước: ' \|\| strftime(date_trunc('week', current_date) - INTERVAL '7 days', '%d/%m/%Y') \|\| ' → ' \|\| strftime(date_trunc('week', current_date) - INTERVAL '1 day', '%d/%m/%Y') AS " "` |
| Monthly | `SELECT '📅 Tháng này: ' \|\| strftime(date_trunc('month', current_date), '%d/%m/%Y') \|\| ' → ' \|\| strftime(current_date, '%d/%m/%Y') \|\| '  ·  Tháng trước: ' \|\| strftime(date_trunc('month', current_date) - INTERVAL '1 month', '%d/%m/%Y') \|\| ' → ' \|\| strftime(date_trunc('month', current_date) - INTERVAL '1 day', '%d/%m/%Y') AS " "` |

**Column alias phải là `" "` (single space)** — nếu đặt tên thật (vd `"Chu kỳ báo cáo"`), Metabase render tên cột thay vì giá trị.

**Tên question trong blueprint:** `Chu kỳ báo cáo` (daily), `Chu kỳ báo cáo (Weekly)`, `Chu kỳ báo cáo (Monthly)`.

**Sau mỗi lần redeploy:** `dashcard.background: false` được tự động apply bởi deploy script (v2026-05-27+) — không cần patch tay.

---

---

## 🗄️ SQL Conventions for Blueprints

All SQL in blueprints targets **DuckDB** (via Metabase Native Query). Follow these rules:

### Filtering

```sql
-- Revenue metrics: scope flag + is_active_order (excludes cancelled)
WHERE scope_retail AND is_active_order

-- Order counts (all orders including cancelled): scope flag only
WHERE scope_retail

-- Cancelled orders only:
WHERE scope_retail AND NOT is_active_order

-- Date ranges: use date_trunc + INTERVAL, never hardcoded dates
AND ordered_at >= date_trunc('month', current_date) - INTERVAL '1 month'
AND ordered_at < date_trunc('month', current_date)
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
    SELECT ... WHERE ordered_at >= date_trunc('week', current_date) - INTERVAL '7 days'
                 AND ordered_at < date_trunc('week', current_date)
),
last_week AS (
    SELECT ... WHERE ordered_at >= date_trunc('week', current_date) - INTERVAL '14 days'
                 AND ordered_at < date_trunc('week', current_date) - INTERVAL '7 days'
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
| `scope_sales` | `is_sales_channel` | Executive [All] |
| `scope_retail` | `scope_sales AND customer_type='RETAIL'` | Retail [Retail] |
| `scope_b2b` | `scope_sales AND customer_type IN (WHOLESALE, PARTNER)` | B2B [B2B] |
| `is_active_order` | `status != 'CANCELLED'` — revenue gate, cross-cutting | All layers |

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

### Collection Architecture (6 Collections — restructured 2026-05-27)

We use **6 top-level collections**, each answering one core audience question:

```
📍 Start Here                         ← "Where do I go?" (onboarding)
│   └── Welcome to ChợPulse BI
│
📁 Executive                          ← "Công ty đang thế nào?"
│   ├── CEO Weekly Pulse [All]
│   ├── CEO Monthly Scorecard [All]
│   └── Sales Monthly Business Review [All]
│
📁 Finance                            ← "Tiền của tôi đi đâu?" (NEW 2026-05-27)
│   ├── Finance P&L [All]
│   ├── Order Profitability [All]
│   └── Product Profitability [All]
│   # Roadmap: Cost Ledger, Return Impact, Channel P&L, SKU Margin, Recon
│
📁 Marketing & Customers              ← "Kênh/Khách thế nào?"
│   ├── Marketing Weekly Tracker [Retail]
│   ├── Marketing Monthly Analysis [Retail]
│   ├── Marketing ROI [Retail]
│   ├── Customer Operational [Retail]
│   ├── Customer Retention & Lifecycle [Retail]
│   └── Promotion Analysis [Retail]
│
📁 Operations                         ← "Hôm nay cần làm gì?"
│   ├── US CrossBorder/               [US] (NEW 2026-05-27)
│   │   └── US CrossBorder Daily [US]
│   ├── Daily Monitoring/             [Retail]
│   ├── Periodic Reviews/             [Retail]
│   ├── B2B Operations/               [B2B]
│   ├── Logistics/                    (NEW)
│   └── Data Platform/                (NEW)
│
📁 Analytics                          ← "So sánh segment / deep-dive?" (NEW 2026-05-27 - Layer 3)
│   ├── Customer Intelligence Monthly [Cross]
│   ├── Channel Profitability Monthly [Cross]
│   ├── Product Performance [Cross]
│   └── Shopee Channel Economics [Cross]
```

### Collection Placement Workflow

1. **Identify the audience** of the dashboard.
2. **Ask the decision question:**

   | Question | Collection Path |
   |:---|:---|
   | "Is this for **onboarding**?" (new users) | `📍 Start Here` |
   | "Is this for **strategic oversight**?" (CEO, Board) | `Executive` |
   | "Is this for **financial / cost / profitability**?" (CFO, FP&A, Accounting) | `Finance` |
   | "Is this for **channel/customer analysis**?" (Marketing, CS) | `Marketing & Customers` |
   | "Is this for **daily retail action items**?" (Store Manager) | `Operations > Daily Monitoring` |
   | "Is this for **weekly/monthly retail ops review**?" (Sales Ops Lead) | `Operations > Periodic Reviews` |
   | "Is this for **B2B/wholesale tracking**?" (B2B AM) | `Operations > B2B Operations` |
   | "Is this for **US CrossBorder / export arrangements**?" (US Ops) | `Operations > US CrossBorder` |
   | "Is this for **shipping / delivery ops**?" (Logistics Manager) | `Operations > Logistics` |
   | "Is this for **pipeline / data health**?" (Data Engineering) | `Operations > Data Platform` |
   | "Is this for **cross-segment research**?" (Analyst) | `Analytics` |

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
- **New domain emerges with own audience (e.g., Finance, Logistics)** → create new top-level. *Example 2026-05-27: Finance split out when P&L marts (`fact_order_economics`, `fact_order_costs`, `fact_order_returns`) created.*

### Archive Policy (NEW 2026-05-27)
When renaming a dashboard via blueprint, declare aliases in frontmatter:
```yaml
---
title: New Name [All]
aliases:
  - Old Name
---
```
The deploy script will auto-archive the old name on next deploy. This prevents the "7 duplicate pairs" situation discovered in audit 2026-05-27.

### Validation
- Pre-commit hook: `node .skills/metabase-automation/scripts/validate-collections.js --mode=pre-commit`
- Daily Dagster job: posts to Lark if drift detected between `collection_registry.yml` and live Metabase
- See [plans/260527-1327-metabase-collection-restructure/phase-07](../../plans/260527-1327-metabase-collection-restructure/phase-07-validation-rollout.md)

---

## 📂 4. Design Spec File Structure (`designs/*.md`) — NEW

**Purpose:** Tool-agnostic design specification — contract between Analytics Design (Phase 0-6) and Metabase Automation (Phase 7-10).
**Filename Convention:** Same as playbook/blueprint (e.g., `ceo_weekly_pulse.md`).
**Created by:** Analytics Design Skill (`.skills/analytics-design/`)

**Required document definition:** Every new design spec file MUST include the following block immediately after the `## Design Spec: ...` title:

```markdown
> **Tài liệu này là bản thiết kế tool-agnostic cho dashboard/report.**
> Nó chuyển playbook thành cấu trúc trình bày cụ thể: views, card roles, loại biểu đồ chuẩn, bộ lọc, thứ tự đọc, so sánh cần có, màu sắc/kích thước theo semantic tokens và các yêu cầu trải nghiệm phân tích.
> Design spec là hợp đồng giữa Analytics Design và bước triển khai BI; nó không phụ thuộc vào bất kỳ công cụ BI hay nền tảng triển khai cụ thể nào, nhưng được dùng làm input để tạo blueprint triển khai cho công cụ BI được chọn.
```

### Template

```markdown
---
title: [Dashboard Title]
archetype: [Executive Pulse / Operational Cockpit / Exploratory Tool]
status: [final / draft / draft-from-capture]
last_modified: YYYY-MM-DD
domain_refs: [domains/sales.md, domains/customer.md]
---

## Design Spec: [Dashboard Title]

> **Tài liệu này là bản thiết kế tool-agnostic cho dashboard/report.**
> Nó chuyển playbook thành cấu trúc trình bày cụ thể: views, card roles, loại biểu đồ chuẩn, bộ lọc, thứ tự đọc, so sánh cần có, màu sắc/kích thước theo semantic tokens và các yêu cầu trải nghiệm phân tích.
> Design spec là hợp đồng giữa Analytics Design và bước triển khai BI; nó không phụ thuộc vào bất kỳ công cụ BI hay nền tảng triển khai cụ thể nào, nhưng được dùng làm input để tạo blueprint triển khai cho công cụ BI được chọn.
```

Sections: Brief, Constraints & Filters, Views, Composition (table with Role, Viz Type, Color tokens, Size tokens).

See full template: `.skills/analytics-design/templates/design_spec_template.md`

**Key traits:**
- Uses **YAML frontmatter** (unlike domains/playbooks which use blockquote metadata) — needed for staleness detection
- Uses **standard vocabulary** for viz types (not Metabase display types)
- Uses **semantic tokens** for colors and sizes (not hex codes or pixels)
- `status: draft-from-capture` marks reverse-generated specs that need analyst review

---

## 📐 Semantic Layer

### Thứ bậc ảnh hưởng

```
Domain (WHY)     domains/*.md          — bối cảnh kinh doanh, lý do đo lường
    ↓ drives
Semantic (WHAT)  semantic/*.md         — definition chuẩn, machine-readable
    ↓ constrains
Implementation   mart columns          — fact_orders.scope_retail
                 Rill YAML             — rill/metrics/*.yaml
                 Blueprint SQL         — blueprints/*.md
```

Domain **drives** semantic — semantic formalize domain decision, không tự quyết business rule. Khi semantic gặp ambiguity → đẩy ngược lên domain để clarify.

### Semantic files

| File | Nội dung |
|---|---|
| `semantic/segments.md` | scope_retail, scope_b2b, scope_sales |
| `semantic/metrics.md` | net_revenue, gross_revenue, AOV, discount_rate |
| `semantic/dimensions.md` | channel_name, customer_type, date_key |
| `semantic/entities.md` | order, customer, product, channel |
| `semantic/rules.md` | VAT treatment, cancellation, is_completed, date_key ICT |
| `semantic/freshness.md` | data SLA per mart table |

### Quy tắc bắt buộc khi viết Blueprint SQL

1. **Đọc `semantic/` trước** — xác định concepts nào sẽ dùng
2. **Dùng pre-computed columns** — không re-derive từ raw conditions:
   ```sql
   -- ✅
   WHERE scope_retail
   -- ❌
   WHERE customer_type = 'RETAIL' AND is_sales_channel = true AND status NOT IN (...)
   ```
3. **Khai báo `uses_concepts:` và `issues:` trong frontmatter** của blueprint:
   ```yaml
   ---
   uses_concepts: [scope_retail, net_revenue, discount_rate]
   issues:                    # optional — problems found during build/review
     - "[warn] Card: AOV — includes B2B if scope not filtered correctly"
     - "[todo] Card: New Customers — verify cancelled-order customers should count"
   ---
   ```
   `issues` là metadata thuần (không parse bởi deploy script). Dùng tags `[error]`/`[warn]`/`[info]`/`[todo]`. Xem format đầy đủ tại `semantic/README.md → Blueprint Integration Standard`.
4. **Metric mới** → thêm vào `semantic/metrics.md` trước, implement mart column, rồi mới viết blueprint

### Quy tắc bắt buộc khi thêm Semantic concept mới

1. Domain team xác nhận business rule
2. Thêm definition vào `semantic/*.md`
3. Implement column trong dbt mart
4. Update Rill YAML nếu Rill cần dùng
5. Blueprint dùng column — không viết lại rule trong SQL

---

## 📋 Artifact Ownership

| Directory | Owned by | Skill knowledge |
|-----------|----------|-----------------|
| `domains/` | Analytics Design | `.skills/analytics-design/*` |
| `semantic/` | Analytics Design | `semantic/README.md` |
| `playbooks/` | Analytics Design | `.skills/analytics-design/*` |
| `guides/` | Analytics Design | `.skills/analytics-design/*` |
| `designs/` | Analytics Design | `.skills/analytics-design/*` |
| `blueprints/` | Metabase Automation | `.skills/metabase-automation/*` |

**Creation order**: domain → semantic → playbook → [guide] → design spec → blueprint → deploy

---

## ⚡ Workflow Checklist for Agents

When user requests: _"Add a Customer LTV chart to the Executive Dashboard."_

1.  **Search Domains:** Does `Customer LTV` exist in any `domains/*.md`?
    - _If No:_ Create it in `domains/customer.md` with SQL logic.
2.  **Check Semantic:** Does `Customer LTV` have a definition in `semantic/metrics.md`?
    - _If No:_ Add definition + formula. Implement mart column if needed.
    - _If Yes:_ Note the canonical formula and required scope.
3.  **Update Playbook:** Open `playbooks/executive_dashboard.md`.
    - Add a row to the Visualization table.
    - **CRITICAL:** Insert the link: `[Customer LTV](../domains/customer.md#customer-ltv)`.
3.  **Update Design Spec:** Open `designs/executive_dashboard.md` (if exists).
    - Add new card to Composition table with role, viz type, color/size tokens.
    - Update `last_modified` in frontmatter.
4.  **Check Collection Registry:** Read `collection_registry.yml` to confirm the target collection path. If creating a NEW dashboard:
    - Pick scope suffix per **Rule 6** (`[All]/[Retail]/[B2B]/[Cross]/[US]/[Internal]`).
    - **Register the dashboard name (with suffix) in `collection_registry.yml` FIRST** under the chosen collection's `dashboards:` list. Skipping this step → deploy lands the dashboard in root + creates duplicates on later renames.
5.  **Create/Update Blueprint:** Translate Design Spec → blueprint using `METABASE_VIZ_CATALOG.md`. Ensure scope suffix is consistent across 4 places: `dashboard_name:` YAML, h1, h3, registry entry.
6.  **Deploy (Optional):** Use `/deploy-metabase-blueprint` to push to Metabase.

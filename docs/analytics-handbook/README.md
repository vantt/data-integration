# Analytics Handbook

Welcome to the **Analytics Handbook**. This directory is the single source of truth for our Business Intelligence logic and visualization standards.

## Architecture Philosophy

We follow a **"Domain-First"** approach.

1. **Domains (`/domains`)**: The "WHY" and "WHAT".

   - Defines the business logic, metrics, and "laws" of the business.
   - Metrics are **grouped** by domain (e.g., `finance.md`, `supply_chain.md`).
   - _Rule:_ Never define a metric (logic) directly in a dashboard. Define it here first.
2. **Playbooks (`/playbooks`)**: The "PRODUCTS" and "HOW".

   - Describes specific Dashboards and Reports (e.g., `sales_executive_dashboard.md`).
   - Focuses on Layout, User Stories, and Visualization settings.
   - _Rule:_ Reference concepts from the Domain files. Do not repeat logic.
3. **Blueprints (`/blueprints`)**: The "SPECS" and "IMPLEMENTATION".

   - Contains detailed technical specifications (SQL queries, JSON configs).
   - Serves as the implementation reference for Machines/Agents.
   - **Deployable:** Can be automatically pushed to Metabase using the `/deploy_metabase_blueprint` workflow.
   - _Rule:_ While Playbooks are for humans (Why/What), Blueprints are for machines (How).

## Directory Structure

```text
docs/analytics-handbook/
├── domains/                    <-- The "Laws" (Business Logic & Metrics)
│   ├── sales.md
│   ├── finance.md
│   └── ...
│
├── playbooks/                  <-- The "Products" (Dashboards)
│   ├── ceo_weekly_pulse.md
│   ├── sales_daily_operation.md
│   ├── rill/                   <-- Rill-specific playbooks
│   │   ├── orders_executive.md
│   │   ├── orders_retail_ops.md
│   │   └── orders_b2b_ops.md
│   └── ...
│
├── blueprints/                 <-- The "Specs" (Technical Implementation)
│   ├── ceo_weekly_pulse.md     <-- Metabase blueprints
│   ├── rill/                   <-- Rill blueprints (YAML)
│   │   ├── orders_executive.yaml
│   │   ├── orders_retail_ops.yaml
│   │   └── orders_b2b_ops.yaml
│   └── ...
│
├── guides/                     <-- The "Knowledge" (Concepts & Patterns)
│   ├── report_segmentation.md  <-- 3-layer architecture guide
│   ├── metabase_concepts.md
│   └── ...
│
├── AGENTS.md                   <-- Instructions for AI Assistants
└── README.md                   <-- This file
```

## Platform Support

| Platform | Playbooks | Blueprints | Deployment |
|----------|-----------|------------|------------|
| **Metabase** | `playbooks/*.md` | `blueprints/*.md` | `/deploy_metabase_blueprint` |
| **Rill** | `playbooks/rill/*.md` | `blueprints/rill/*.yaml` | Copy to `rill/dashboards/` |

## 3-Layer Architecture

All dashboards follow a 3-layer scope architecture (see [Report Segmentation Guide](guides/report_segmentation.md)):

```
Layer 1: Executive [All]     → scope_sales = true
Layer 2: Retail [Retail]     → scope_retail = true  
Layer 2: B2B [B2B]           → scope_b2b = true
Layer 3: Analytics [Cross]   → Explicit per-analysis
```

## Workflow for Contributors

1. **Request:** "We need a chart showing Profit Margin."
2. **Step 1 (Check Domains):** Is `Profit Margin` defined in `domains/finance.md`?
   - _No:_ Create definition. Map it to `dbt model`.
   - _Yes:_ Note the Anchor Link (e.g., `finance.md#profit-margin`).
3. **Step 2 (Update Playbook):** Open the relevant Playbook (e.g., `executive_overview.md`).
   - Add a new Chart section.
   - Link to the Domain definition.
   - Describe the visualization settings (Line chart, Green color, etc.).
4. **Step 3 (Spec):** If complex, create `blueprints/sales_dashboard.md` with exact SQL/JSON.
5. **Step 4 (Deploy):** Use the `/deploy_metabase_blueprint` workflow to push to Metabase.

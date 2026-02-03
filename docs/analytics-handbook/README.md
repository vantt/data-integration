# Analytics Handbook

Welcome to the **Analytics Handbook**. This directory is the single source of truth for our Business Intelligence logic and visualization standards.

## Architecture Philosophy

We follow a **"Domain-First"** approach.

1.  **Domains (`/domains`)**: The "WHY" and "WHAT".
    - Defines the business logic, metrics, and "laws" of the business.
    - Metrics are **grouped** by domain (e.g., `finance.md`, `supply_chain.md`).
    - _Rule:_ Never define a metric (logic) directly in a dashboard. Define it here first.

2.  **Playbooks (`/playbooks`)**: The "PRODUCTS" and "HOW".
    - Describes specific Dashboards and Reports (e.g., `sales_executive_dashboard.md`).
    - Focuses on Layout, User Stories, and Visualization settings.
    - _Rule:_ Reference concepts from the Domain files. Do not repeat logic.

3.  **Blueprints (`/blueprints`)**: The "SPECS" and "IMPLEMENTATION".
    - Contains detailed technical specifications (SQL queries, JSON configs).
    - Serves as the implementation reference for Machines/Agents.
    - **Deployable:** Can be automatically pushed to Metabase using the `/deploy_metabase_blueprint` workflow.
    - _Rule:_ While Playbooks are for humans (Why/What), Blueprints are for machines (How).

## Directory Structure

```text
docs/analytics-handbook/
├── domains/                    <-- The "Laws" (Business Logic & Metrics)
│   ├── finance.md
│   ├── supply_chain.md
│   └── ...
│
├── playbooks/                  <-- The "Products" (Dashboards)
│   ├── executive_overview.md
│   ├── sales_daily_operation.md
│   └── ...
│
├── blueprints/                 <-- The "Specs" (Technical Implementation)
│   ├── sales_daily.md
│   └── ...
│
├── guides/                     <-- The "Knowledge" (Concepts & Patterns)
│   ├── metabase_concepts.md
│   └── ...
│
├── AGENTS.md                   <-- Instructions for AI Assistants
└── README.md                   <-- This file
```

## Workflow for Contributors

1.  **Request:** "We need a chart showing Profit Margin."
2.  **Step 1 (Check Domains):** Is `Profit Margin` defined in `domains/finance.md`?
    - _No:_ Create definition. Map it to `dbt model`.
    - _Yes:_ Note the Anchor Link (e.g., `finance.md#profit-margin`).
3.  **Step 2 (Update Playbook):** Open the relevant Playbook (e.g., `executive_overview.md`).
    - Add a new Chart section.
    - Link to the Domain definition.
    - Describe the visualization settings (Line chart, Green color, etc.).
4.  **Step 3 (Spec):** If complex, create `blueprints/sales_dashboard.md` with exact SQL/JSON.
5.  **Step 4 (Deploy):** Use the `/deploy_metabase_blueprint` workflow to push to Metabase.

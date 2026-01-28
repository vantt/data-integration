# Metabase Implementation Strategy (The Brain)

This document provides the **Cognitive Framework** for implementing analytics. Do not just execute code; apply these patterns to deliver value.

## 1. Dashboard Archetypes (Architecture)

Before coding, identify the **Archetype** of the dashboard:

| Archetype                 | Purpose                    | Layout Strategy                                                                                                                                      |
| :------------------------ | :------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Executive "Pulse"**     | High-level health check.   | **Top:** Big Number KPIs (Growth %).<br>**Middle:** Trend Lines (Year-over-Year).<br>**Bottom:** No tables, only alerts.                             |
| **Operational "Cockpit"** | Daily management / Action. | **Top:** Global Filters (Date, Region).<br>**Middle:** Bar Charts (Categorical breakdowns).<br>**Bottom:** High-density Table (transaction details). |
| **Exploratory "tool"**    | Deep dive analysis.        | **Sidebar:** Many filters.<br>**Main:** Large Pivot Table or Scatter Plot.<br>**Goal:** Allow slicing/dicing.                                        |

**👉 Rule:** If the user asks for "Sales Dashboard", default to **Operational "Cockpit"** unless specified otherwise.

## 2. Visualization Heuristics (Design Thinking)

Choose the right tool for the data shape:

- **Time Series**:
  - _< 3 Categories_: Multi-line Chart.
  - _Many Categories_: Stacked Area Chart.
- **Comparison**:
  - _Nominal (Product A vs B)_: Horizontal Bar Chart (readable labels).
  - _Part-to-Whole_: Donut Chart (Max 5 slices, otherwise use Table).
- **KPIS**:
  - Always enable "Trend" comparison if previous period data exists.

## 3. Semantic Layer Strategy (Data Modeling)

Do not pollute Metabase with raw SQL fragments. Use the **Pyramid Principle**:

1.  **Base (Models)**: Create a "Trusted Dataset" (Model) (`dataset: true`) for core entities (e.g., `Official Orders`).
    - _Why_: Hides complex Joins/Casting from non-technical users.
2.  **Middle (Metrics)**: Define standard calculations (e.g., `Revenue`, `AOV`) on the Model.
    - _Why_: Ensures "Revenue" is calculated identically everywhere.
3.  **Top (Questions)**: Only visuals should be "Questions".
    - _Rule_: A Dashboard Question should rarely have raw SQL. It should query a **Model**.

## 4. Automation Workflow

When receiving a request:

1.  **Classify**: Is this a _Pulse_, _Cockpit_, or _Tool_?
2.  **Model**: Does a `Model` already exist for this data? If no, **Create Model First**.
3.  **Visualize**: Apply Heuristics to choose charts.
4.  **Assemble**: Script the deployment.

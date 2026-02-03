# Playbook: Finance Cash Flow

## Overview

- **Audience:** CFO, Treasury
- **Goal:** Track cash movements, forecast, and monitor liquidity.
- **Metabase Collection:** `Finance Analytics`

## Data Lineage

- **Core Model:** `fact_payments` (Planned)
- **Dimensions:** [`dim_date`](../../../transformation/models/marts/core/dim_date.sql)

## Filters

- **Date Range:** Last 90 Days (default).

## Visualizations

### Section 1: Liquidity Position

| Chart Title                | Visualization Type | Metric Reference (Link to Domain)                          | Notes/Config       |
| :------------------------- | :----------------- | :--------------------------------------------------------- | :----------------- |
| **Cash Balance**           | Scalar             | [Net Cash Flow](../domains/finance.md#11-net-cash-flow)    | Current Balance.   |
| **Days Sales Outstanding** | Scalar             | [DSO](../domains/finance.md#10-days-sales-outstanding-dso) | Target: < 30 days. |

### Section 2: Movement & Forecast

| Chart Title             | Visualization Type | Metric Reference (Link to Domain)                       | Notes/Config                             |
| :---------------------- | :----------------- | :------------------------------------------------------ | :--------------------------------------- |
| **Daily Cash Movement** | Combo Chart        | [Net Cash Flow](../domains/finance.md#11-net-cash-flow) | Line: Net Movement, Bar: Inflow/Outflow. |
| **Cash Flow Forecast**  | Line Chart         | [Net Cash Flow](../domains/finance.md#11-net-cash-flow) | Projected values based on AP/AR.         |

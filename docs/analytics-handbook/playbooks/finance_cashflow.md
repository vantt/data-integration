# Playbook: Finance Cash Flow

## Overview

- **Audience:** CFO, Treasury
- **Goal:** Track cash movements, forecast, and monitor liquidity.
- **Metabase Collection:** `Finance Analytics`

## Filters

- **Date Range:** Last 90 Days (default).

## Visualizations

### Section 1: Liquidity Position

| Chart Title                | Visualization Type | Metric Reference (Link to Domain)                         | Notes/Config       |
| :------------------------- | :----------------- | :-------------------------------------------------------- | :----------------- |
| **Cash Balance**           | Scalar             | [Net Cash Flow](../domains/finance.md#10-net-cash-flow)   | Current Balance.   |
| **Days Sales Outstanding** | Scalar             | [DSO](../domains/finance.md#9-days-sales-outstanding-dso) | Target: < 30 days. |

### Section 2: Movement & Forecast

| Chart Title             | Visualization Type | Metric Reference (Link to Domain)                       | Notes/Config                             |
| :---------------------- | :----------------- | :------------------------------------------------------ | :--------------------------------------- |
| **Daily Cash Movement** | Combo Chart        | [Net Cash Flow](../domains/finance.md#10-net-cash-flow) | Line: Net Movement, Bar: Inflow/Outflow. |
| **Cash Flow Forecast**  | Line Chart         | [Net Cash Flow](../domains/finance.md#10-net-cash-flow) | Projected values based on AP/AR.         |

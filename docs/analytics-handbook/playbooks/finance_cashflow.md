# Playbook: Finance Cash Flow

> **Status:** DEFERRED — pending data foundation (xem audit report 260528-0834)
> **Blocker:** `fact_payments` exists but lacks inflow/outflow classification. Dashboard blocked until payment type enrichment (AP/AR tagging) is implemented.

## Overview

- **Audience:** CFO, Treasury
- **Goal:** Track cash movements, forecast, and monitor liquidity.
- **Collection:** `Finance`

## Data Lineage

- **Core Model:** [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql) — exists but needs inflow/outflow type enrichment
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

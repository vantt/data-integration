# Playbook: Customer Retention & Churn

## Overview

- **Audience:** Customer Success, Executives
- **Goal:** Track retention rates, identify churn risks, and monitor cohort health.
- **Metabase Collection:** `Customer Operations`

## Data Lineage

- **Core Model:** [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql)
- **Dimensions:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) (for cohort analysis)

## Filters

- **Cohort Month:** Month of customer acquisition (First Order Date).
- **Customer Segment:** VIP, Loyal, Regular.
- **Geography:** Province/City (from `dim_customers`).

## Visualizations

### Section 1: Retention Health Top-line

| Chart Title                | Visualization Type | Metric Reference                                          | Notes/Config                     |
| :------------------------- | :----------------- | :-------------------------------------------------------- | :------------------------------- |
| **Overall Retention Rate** | Scalar             | [Retention Rate](../domains/customer.md#5-retention-rate) | % of customers who repurchased.  |
| **Churn Rate (Monthly)**   | Trend Line         | [Churn Rate](../domains/customer.md#6-churn-rate)         | Trend of `Churned` status count. |
| **At Risk Customers**      | Scalar             | Count of `At Risk`                                        | Immediate action required.       |

### Section 2: Cohort Analysis

| Chart Title                  | Visualization Type | Metric Reference                                          | Notes/Config                                                    |
| :--------------------------- | :----------------- | :-------------------------------------------------------- | :-------------------------------------------------------------- |
| **Cohort Retention Heatmap** | Table / Heatmap    | [Retention Rate](../domains/customer.md#5-retention-rate) | Rows: Cohort Month, Cols: Months Since Join, Cell: % Retention. |
| **Churn Reasons**            | Bar Chart          | Count of Churn Events                                     | (Future) Requires churn survey data.                            |

### Section 3: Risk Watchlist

| Chart Title                | Visualization Type | Columns                                                          | Notes/Config                                                          |
| :------------------------- | :----------------- | :--------------------------------------------------------------- | :-------------------------------------------------------------------- |
| **At Risk Customers List** | Table              | Name, Phone, **Last Order Date**, **Days Since Last Order**, LTV | Filter: Status = 'At Risk'. Sort by LTV DESC (Save high value first). |

## Implementation Notes

- **Cohort Logic:** Ensure the "Cohort Month" uses `first_order_date` truncated to the month.
- **Action Item:** The "Risk Watchlist" is the most critical operational tool. Review it weekly.

# Playbook: Customer Retention & Churn

## Overview

- **Audience:** Customer Success, Executives
- **Goal:** Track retention rates and identify churn risks.
- **Metabase Collection:** `Customer Analytics`

## Filters

- **Cohort Month:** Monthly cohorts.

## Visualizations

### Section 1: Retention Health

| Chart Title        | Visualization Type | Metric Reference (Link to Domain)                         | Notes/Config     |
| :----------------- | :----------------- | :-------------------------------------------------------- | :--------------- |
| **Retention Rate** | Scalar             | [Retention Rate](../domains/customer.md#5-retention-rate) | Overall average. |
| **Churn Rate**     | Scalar / Trend     | [Churn Rate](../domains/customer.md#6-churn-rate)         | Monthly trend.   |

### Section 2: Cohort Analysis

| Chart Title                 | Visualization Type        | Metric Reference (Link to Domain)                         | Notes/Config                                     |
| :-------------------------- | :------------------------ | :-------------------------------------------------------- | :----------------------------------------------- |
| **Cohort Retention Curves** | Line Chart (Multi-series) | [Retention Rate](../domains/customer.md#5-retention-rate) | Series: Cohort Month. X-Axis: Months since join. |
| **Churn Reasons**           | Bar Chart                 | Count of Churn Events                                     | Group by Reason Code.                            |

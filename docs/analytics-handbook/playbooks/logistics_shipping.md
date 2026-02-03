# Playbook: Shipping & Returns

## Overview

- **Audience:** Warehouse Manager, CS
- **Goal:** Monitor carrier performance and return reasons.
- **Metabase Collection:** `Logistics`

## Filters

- **Carrier:** Filter by Delivery Provider.
- **Date Range:** Last 30 Days.

## Visualizations

### Section 1: Carrier Performance

| Chart Title              | Visualization Type | Metric Reference (Link to Domain)                                        | Notes/Config                     |
| :----------------------- | :----------------- | :----------------------------------------------------------------------- | :------------------------------- |
| **Delivery Time Dist**   | Histogram          | [Avg Delivery Time](../domains/logistics.md#4-avg-delivery-time)         | Distribution of days to deliver. |
| **Carrier Success Rate** | Bar Chart          | [On-Time Delivery Rate](../domains/logistics.md#5-on-time-delivery-rate) | Compare carriers.                |

### Section 2: Returns

| Chart Title           | Visualization Type | Metric Reference (Link to Domain)                    | Notes/Config          |
| :-------------------- | :----------------- | :--------------------------------------------------- | :-------------------- |
| **Return Rate Trend** | Line Chart         | [Return Rate](../domains/logistics.md#6-return-rate) | Weekly trend.         |
| **Return Reasons**    | Bar / Pareto       | Count Returns                                        | Group by Reason Code. |

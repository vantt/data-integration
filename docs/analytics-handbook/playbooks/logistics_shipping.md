# Playbook: Shipping & Returns

> **Status:** UNBLOCKED — shipment data available via `fact_fulfillments` (tracking columns added 2026-06-09)
> **Note:** `fact_shipments` + `dim_carriers` not built as standalone, but shipment/carrier fields are embedded in `fact_fulfillments`.

## Overview

- **Audience:** Warehouse Manager, CS
- **Goal:** Monitor carrier performance and return reasons.
- **Collection:** `Operations > Logistics`

## Data Lineage

- **Core Model:** `fact_fulfillments` (shipment tracking columns embedded)
- **Dimensions:** carrier/provider fields in `fact_fulfillments`

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

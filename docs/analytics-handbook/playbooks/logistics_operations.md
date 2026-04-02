# Playbook: Logistics Operations Center

## Overview

- **Audience:** Operations Manager
- **Goal:** Real-time view of order processing pipeline.
- **Collection:** `Logistics`

## Data Lineage

- **Core Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
- **Dimensions:** `dim_logistics` (Planned)

## Filters

- **Date Range:** Today (Real-time).

## Visualizations

### Section 1: Order Funnel

| Chart Title          | Visualization Type | Metric Reference (Link to Domain)                              | Notes/Config                      |
| :------------------- | :----------------- | :------------------------------------------------------------- | :-------------------------------- |
| **Status Funnel**    | Funnel / Bar       | Count Orders by Status                                         | Pending -> Processing -> Shipped. |
| **Fulfillment Rate** | Scalar             | [Fulfillment Rate](../domains/logistics.md#1-fulfillment-rate) | Target: >99%.                     |

### Section 2: Speed & Throughput

| Chart Title           | Visualization Type | Metric Reference (Link to Domain)                              | Notes/Config                        |
| :-------------------- | :----------------- | :------------------------------------------------------------- | :---------------------------------- |
| **Fulfillment Speed** | Line Chart         | [Order Cycle Time](../domains/logistics.md#2-order-cycle-time) | Hourly average cycle time.          |
| **Hourly Throughput** | Heatmap            | Count Shipped Orders                                           | Row: Day of Week, Col: Hour of Day. |

## Implementation Notes

### Best Practices

1. **Status Mapping**: Ensure ERP status codes map cleanly to analytics stages.
2. **Timezones**: Standardize timestamps (UTC) for duration calculations.
3. **Shift Analysis**: Compare performance across AM/PM shifts.
4. **SLA Alerts**: Alert on orders stuck in 'Processing' > 24h.

### Common Pitfalls

- Counting cancelled orders in fulfillment metrics.
- Not excluding weekends/holidays from "Days to Ship" calculation.
- Blaming carriers for warehouse processing delays (start clock correctly).

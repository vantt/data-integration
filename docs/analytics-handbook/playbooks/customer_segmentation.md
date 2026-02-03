# Playbook: Customer Segmentation

## Overview

- **Audience:** Marketing, Product
- **Goal:** Visualize customer segments and demographic characteristics.
- **Metabase Collection:** `Customer Analytics`

## Data Lineage

- **Core Model:** [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql)
- **Dimensions:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)

## Filters

- **Date Range:** Last 12 months.
- **Segment:** Filter by specific RFM segment.

## Visualizations

### Section 1: Segment Overview

| Chart Title              | Visualization Type | Metric Reference (Link to Domain)                   | Notes/Config      |
| :----------------------- | :----------------- | :-------------------------------------------------- | :---------------- |
| **Total Customers**      | Scalar             | Count distinct `customer_id`                        |                   |
| **Segment Distribution** | Donut Chart        | [RFM Segment](../domains/customer.md#7-rfm-segment) | Group by Segment. |

### Section 2: Segment Deep Dive

| Chart Title             | Visualization Type | Metric Reference (Link to Domain)                                                                                           | Notes/Config                            |
| :---------------------- | :----------------- | :-------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------- |
| **Segment Profiles**    | Radar Chart        | [RFM Segment](../domains/customer.md#7-rfm-segment)                                                                         | Axes: Recency, Frequency, Monetary.     |
| **Segment Performance** | Table              | [ARPU](../domains/customer.md#3-arpu-average-revenue-per-user), [CLV](../domains/customer.md#2-customer-lifetime-value-clv) | Columns: Segment, Count, ARPU, AVG CLV. |

## Implementation Notes

### Best Practices

1. **Segment Stability**: Avoid changing segment definitions frequently to maintain trend continuity.
2. **Cohort Consistency**: Always use uniform cohort periods (e.g., Monthly).
3. **Privacy Compliance**: Ensure PII is anonymized in dashboard exports.
4. **Statistical Significance**: Ensure segments have statistically relevant sample sizes.

### Common Pitfalls

- Using current segment assignments for historical analysis (survival bias).
- Ignoring seasonality when analyzing retention.
- Not factoring in Acquisition Channel costs in CLV.

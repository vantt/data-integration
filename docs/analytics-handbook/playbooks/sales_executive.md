# Playbook: Sales Executive Overview

## Overview

- **Audience:** Executives, Leadership
- **Goal:** Strategic overview of sales performance, growth, and high-level KPIs.
- **Metabase Collection:** `Sales Analytics`

## Filters

- **Date Range:** Default to This Month.
- **Comparison:** vs Last Month / vs Same Month Last Year.

## Visualizations

### Section 1: Monthly KPIs

| Chart Title     | Visualization Type | Metric Reference (Link to Domain)                    | Notes/Config                     |
| :-------------- | :----------------- | :--------------------------------------------------- | :------------------------------- |
| **MTD Revenue** | Scalar / Trend     | [Net Revenue](../domains/sales.md#2-net-revenue)     | Show growth % vs Previous Month. |
| **MTD Orders**  | Scalar             | [Total Orders](../domains/sales.md#3-total-orders)   |                                  |
| **Average AOV** | Scalar             | [AOV](../domains/sales.md#4-aov-average-order-value) |                                  |

### Section 2: Strategic Analysis

| Chart Title               | Visualization Type | Metric Reference (Link to Domain)                          | Notes/Config                                            |
| :------------------------ | :----------------- | :--------------------------------------------------------- | :------------------------------------------------------ |
| **Monthly Revenue Trend** | Combo Chart        | [Net Revenue](../domains/sales.md#2-net-revenue)           | Bar: Current Year, Line: Previous Year. Group by Month. |
| **Channel Performance**   | Table / Pivot      | [Sales by Channel](../domains/sales.md#6-sales-by-channel) | Include metrics: Revenue, Orders, AOV per Channel.      |

## Visualization Configs

### Monthly Revenue Trend

```json
{
  "display": "line",
  "x_axis": "order_date",
  "y_axis": "revenue",
  "visualization_settings": {
    "graph.dimensions": ["order_date"],
    "graph.metrics": ["revenue"]
  }
}
```

## Implementation Notes

### Data Freshness SLA

- Orders: < 5 minutes delay
- Customer data: < 1 hour delay
- Product catalog: < 24 hours delay

### Best Practices

1. **Caching**: Enable 1-hour cache for executive dashboards.
2. **Permissions**: Use Collection-based access control.
3. **Filters**: Always include date range and location filters.

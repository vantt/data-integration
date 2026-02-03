# Playbook: Sales Executive Overview

## Overview

- **Audience:** Executives, Leadership
- **Goal:** Strategic overview of sales performance, growth, and high-level KPIs.
- **Metabase Collection:** `Sales Analytics`
- **Blueprint:** [Technical Spec](../blueprints/sales_executive.md)

## Filters

- **Date Range:** Default to This Month.
- **Comparison:** vs Last Month / vs Same Month Last Year.

## Data Lineage

- **Core Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
- **Dimensions:** `dim_customers`, `dim_locations`, `dim_channels`

## Visualizations

### Section 1: Monthly KPIs

| Chart Title     | Visualization Type | Metric Reference (Link to Domain)                    | Notes/Config                     |
| :-------------- | :----------------- | :--------------------------------------------------- | :------------------------------- |
| **MTD Revenue** | Scalar / Trend     | [Net Revenue](../domains/sales.md#2-net-revenue)     | Show growth % vs Previous Month. |
| **MTD Orders**  | Scalar             | [Total Orders](../domains/sales.md#3-total-orders)   |                                  |
| **Average AOV** | Scalar             | [AOV](../domains/sales.md#4-aov-average-order-value) |                                  |

### Section 2: Strategic Analysis

| Chart Title               | Visualization Type | Metric Reference (Link to Domain)                                     | Notes/Config                                            |
| :------------------------ | :----------------- | :-------------------------------------------------------------------- | :------------------------------------------------------ |
| **Monthly Revenue Trend** | Combo Chart        | [Net Revenue](../domains/sales.md#2-net-revenue)                      | Bar: Current Year, Line: Previous Year. Group by Month. |
| **Channel Performance**   | Table / Pivot      | [Sales by Channel](../domains/sales.md#6-sales-by-channel)            | Include metrics: Revenue, Orders, AOV per Channel.      |
| **Sales by Region**       | Map / Table        | [Sales by Region](../domains/sales.md#13-sales-by-regionlocation)     | Revenue by Region.                                      |
| **Promotion Impact**      | Table              | [Promotion Performance](../domains/sales.md#12-promotion-performance) | Revenue and Usage by Promo.                             |
| **Discount Overview**     | Scalar             | [Discount Impact](../domains/sales.md#11-discount-impact)             | Total Discount Value & Avg Discount %.                  |

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

### Sales by Region (Map)

```json
{
  "display": "map",
  "map.region": "us_states",
  "map.metric": "revenue"
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

# Playbook: Daily Sales Operations

## Overview

- **Audience:** Store Managers, Sales Team
- **Goal:** Real-time monitoring of today's sales performance and operational anomalies.
- **Metabase Collection:** `Daily Operations`

## Filters

- **Date Range:** Default to Today (Real-time).
- **Location:** Filter by Store/Region.

## Visualizations

### Section 1: Real-time Snapshot

| Chart Title             | Visualization Type | Metric Reference (Link to Domain)                        | Notes/Config  |
| :---------------------- | :----------------- | :------------------------------------------------------- | :------------ |
| **Total Revenue Today** | Scalar / Number    | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | Filter: Today |
| **Orders Today**        | Scalar / Number    | [Total Orders](../domains/sales.md#3-total-orders)       | Filter: Today |
| **Average Order Value** | Scalar / Number    | [AOV](../domains/sales.md#4-aov-average-order-value)     | Filter: Today |

### Section 2: Trends & Breakdowns

| Chart Title            | Visualization Type | Metric Reference (Link to Domain)                                    | Notes/Config                                                       |
| :--------------------- | :----------------- | :------------------------------------------------------------------- | :----------------------------------------------------------------- |
| **Hourly Sales Trend** | Line Chart         | [Hourly Sales Trend](../domains/sales.md#5-hourly-sales-trend)       | Compare Today vs Yesterday. Color: Blue (Today), Grey (Yesterday). |
| **Sales by Channel**   | Pie Chart          | [Sales by Channel](../domains/sales.md#6-sales-by-channel)           | Show % breakdown.                                                  |
| **Top Products Today** | Table (Top 10)     | [Top Selling Products](../domains/sales.md#7-top-selling-products)   | Columns: Product Name, Units Sold, Revenue. Sort by Revenue DESC.  |
| **New vs Returning**   | Bar / Number       | [New vs Returning](../domains/sales.md#8-new-vs-returning-customers) | Count of orders per segment.                                       |

## Visualization Configs

### Hourly Sales Trend

```json
{
  "display": "line",
  "graph.dimensions": ["hour_of_day"],
  "graph.metrics": ["sales_today", "sales_yesterday"],
  "graph.colors": ["#509EE3", "#CCCCCC"]
}
```

### Daily Metrics Table

```json
{
  "display": "table",
  "table.pivot": false,
  "table.cell_column": "Total Revenue"
}
```

### Top Channels (Pie)

```json
{
  "display": "pie",
  "pie.dimension": "Channel",
  "pie.metric": "Revenue"
}
```

# Playbook: Yesterday's Sales Operations

## Overview

- **Audience:** Store Managers, Sales Team, Operations Lead
- **Goal:** Review yesterday's finalized sales performance, identify day-over-day changes, and spot anomalies for action.
- **Metabase Collection:** `Daily Operations`
- **Blueprint:** [Technical Spec](../blueprints/sales_yesterday_operation.md)

## Filters

- **Date:** Fixed to Yesterday (auto). Optional override for any past single day.
- **Location:** Filter by Store/Region.

## Data Lineage

- **Core Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
- **Dimensions:** `dim_channels`, `dim_products`, `dim_customers`

## Visualizations

### Section 1: Yesterday's Summary (Finalized)

| Chart Title              | Visualization Type | Metric Reference (Link to Domain)                        | Notes/Config                                           |
| :----------------------- | :----------------- | :------------------------------------------------------- | :----------------------------------------------------- |
| **Total Revenue**        | Scalar / Number    | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | Yesterday's final number. Show DoD % change.           |
| **Net Revenue**          | Scalar / Number    | [Net Revenue](../domains/sales.md#2-net-revenue)         | GMV minus discounts/returns. Show DoD % change.        |
| **Total Orders**         | Scalar / Number    | [Total Orders](../domains/sales.md#4-total-orders)       | Show DoD % change.                                     |
| **AOV**                  | Scalar / Number    | [AOV](../domains/sales.md#5-aov-average-order-value)     | Show DoD % change.                                     |
| **Return Count**         | Scalar / Number    | [Return Rate](../domains/sales.md#3-return-rate--count)  | Highlight if above threshold.                          |
| **Discount Impact**      | Scalar / Number    | [Discount Impact](../domains/sales.md#13-discount-impact) | Total discount amount & % of orders with discount.     |

### Section 2: Hourly Breakdown & Comparisons

| Chart Title                    | Visualization Type | Metric Reference (Link to Domain)                          | Notes/Config                                                              |
| :----------------------------- | :----------------- | :--------------------------------------------------------- | :------------------------------------------------------------------------ |
| **Hourly Sales (Yesterday)**   | Line Chart         | [Hourly Sales Trend](../domains/sales.md#6-hourly-sales-trend) | Yesterday vs Day-Before-Yesterday. Color: Blue (Yest), Grey (D-2). |
| **Sales by Channel**           | Pie Chart          | [Sales by Channel](../domains/sales.md#8-sales-by-channel)    | Show % breakdown for yesterday.                                       |
| **Top Products Yesterday**     | Table (Top 10)     | [Top Selling Products](../domains/sales.md#9-top-selling-products) | Columns: Product, Units Sold, Revenue. Sort Revenue DESC.         |
| **New vs Returning Customers** | Bar / Number       | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Count of orders per segment.                                   |
| **Payment Methods**            | Pie Chart          | [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution) | Breakdown by method.                             |

## Visualization Configs

### Hourly Sales (Yesterday vs D-2)

```json
{
  "display": "line",
  "graph.dimensions": ["hour_of_day"],
  "graph.metrics": ["sales_yesterday", "sales_day_before"],
  "graph.colors": ["#509EE3", "#CCCCCC"]
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

### Payment Methods (Pie)

```json
{
  "display": "pie",
  "pie.dimension": "payment_method_name",
  "pie.metric": "transaction_count"
}
```

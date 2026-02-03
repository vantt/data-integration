# Playbook: Product Performance

## Overview

- **Audience:** Merchandising, Management
- **Goal:** Monitor sales velocity and revenue contribution by product.
- **Metabase Collection:** `Product Analytics`

## Data Lineage

- **Core Model:** [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql)
- **Dimensions:** [`dim_products`](../../../transformation/models/marts/core/dim_products.sql)

## Filters

- **Category:** Filter by Product Category.
- **Date Range:** Last 30 Days.

## Visualizations

### Section 1: Sales Velocity

| Chart Title              | Visualization Type | Metric Reference (Link to Domain)                          | Notes/Config               |
| :----------------------- | :----------------- | :--------------------------------------------------------- | :------------------------- |
| **Revenue Contribution** | Treemap            | [Product Revenue](../domains/product.md#2-product-revenue) | Size by Revenue.           |
| **Top Movers**           | Bar Chart          | [Units Sold](../domains/product.md#1-units-sold)           | Top 20 products by volume. |

### Section 2: Category Analysis

| Chart Title            | Visualization Type | Metric Reference (Link to Domain)                          | Notes/Config                 |
| :--------------------- | :----------------- | :--------------------------------------------------------- | :--------------------------- |
| **Category Mix Trend** | Stacked Area       | [Product Revenue](../domains/product.md#2-product-revenue) | Group by Category Over Time. |
| **Return Rate by Cat** | Bar Chart          | [Return Rate](../domains/product.md#4-return-rate)         |                              |

## Implementation Notes

### Best Practices

1. **ABC Analysis**: Classify products (A=Top 20%, B=Next 30%, C=Bottom 50%) for inventory prioritization.
2. **Seasonality**: Compare velocity against the same period last year.
3. **Bundling**: Analyze "frequently bought together" patterns for upsell opportunities.
4. **Historical Stock**: Snapshot inventory levels daily to enable trend analysis.

### Common Pitfalls

- Ignoring returns when calculating net product revenue.
- Calculating days of supply based on average instead of peak demand.
- Not differentiating new product launches from slow movers in analysis.

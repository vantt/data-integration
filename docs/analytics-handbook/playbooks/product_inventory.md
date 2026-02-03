# Playbook: Inventory Health

## Overview

- **Audience:** Inventory Managers
- **Goal:** Optimization of stock levels and dead stock identification.
- **Metabase Collection:** `Product Analytics`

## Filters

- **Warehouse/Location:** Optional.

## Visualizations

### Section 1: Stock Status

| Chart Title         | Visualization Type | Metric Reference (Link to Domain)                                        | Notes/Config           |
| :------------------ | :----------------- | :----------------------------------------------------------------------- | :--------------------- |
| **Stock Status**    | Gauge              | [Out of Stock (OOS) Rate](../domains/product.md#6-out-of-stock-oos-rate) | Green: <5%, Red: >10%. |
| **Inventory Value** | Scalar             | `Sum(Quantity * Cost)`                                                   | Total capital tied up. |

### Section 2: Efficiency

| Chart Title            | Visualization Type | Metric Reference (Link to Domain)                                         | Notes/Config                                 |
| :--------------------- | :----------------- | :------------------------------------------------------------------------ | :------------------------------------------- |
| **Slow Moving Stock**  | Table              | [Slow-Moving Stock](../domains/product.md#7-slow-moving-stock-dead-stock) | List products with >90 days since last sale. |
| **Stock Cover by Cat** | Bar Chart          | [Days of Supply](../domains/product.md#5-days-of-supply)                  | Avg days of supply per category.             |

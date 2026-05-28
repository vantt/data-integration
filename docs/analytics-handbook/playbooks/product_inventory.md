# Playbook: Inventory Health

> **Status:** DEFERRED — pending data foundation (xem audit report 260528-0834)
> **Blocker:** `fact_inventory` table not yet built. Dashboard blocked until inventory mart is implemented.

## Overview

- **Audience:** Inventory Managers
- **Goal:** Optimization of stock levels and dead stock identification.
- **Collection:** `Analytics`

## Filters

- **Warehouse/Location:** Optional.

## Data Lineage

- **Core Model:** `fact_inventory` (Planned)
- **Dimensions:** [`dim_products`](../../../transformation/models/marts/core/dim_products.sql)

## Visualizations

### Section 1: Stock Status

| Chart Title         | Visualization Type | Metric Reference (Link to Domain)                                        | Notes/Config           |
| :------------------ | :----------------- | :----------------------------------------------------------------------- | :--------------------- |
| **Stock Status**    | Gauge              | [Out of Stock (OOS) Rate](../domains/product.md#7-out-of-stock-oos-rate) | Green: <5%, Red: >10%. |
| **Inventory Value** | Scalar             | [Inventory Value](../domains/product.md#8-inventory-value)               | Total capital tied up. |

### Section 2: Efficiency

| Chart Title            | Visualization Type | Metric Reference (Link to Domain)                                         | Notes/Config                                 |
| :--------------------- | :----------------- | :------------------------------------------------------------------------ | :------------------------------------------- |
| **Slow Moving Stock**  | Table              | [Slow-Moving Stock](../domains/product.md#9-slow-moving-stock-dead-stock) | List products with >90 days since last sale. |
| **Stock Cover by Cat** | Bar Chart          | [Days of Supply](../domains/product.md#6-days-of-supply)                  | Avg days of supply per category.             |

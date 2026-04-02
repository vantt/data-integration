# Playbook: Social Commerce Operations

## Overview

- **Audience:** Customer Support Team Leader
- **Goal:** Monitor and improve the "Chat-to-Order" conversion rate from Facebook & Zalo.
- **Collection:** `Customer Support`

## Key Questions

1. **Are we hitting our daily sales targets from Social?**
2. **Which channel (FB vs Zalo) is driving more value today?**
3. **Are there "missed opportunities" (high traffic but low orders)?** _(Requires future traffic data)_

## Visualizations

### Section 1: Real-time Social Performance

| Chart Title              | Visualization Type | Metric Reference                                                            | Notes                         |
| :----------------------- | :----------------- | :-------------------------------------------------------------------------- | :---------------------------- |
| **Social Revenue Today** | Scalar / Number    | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Filter: Today, Source: Social |
| **Social Orders Today**  | Scalar / Number    | [Social Order Count](../domains/customer_support.md#2-social-order-count)   | Filter: Today, Source: Social |
| **Revenue by Channel**   | Pie Chart          | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Breakdown by Facebook / Zalo  |

### Section 2: Team Performance (Sales Contribution)

> **Note:** Currently tracking _Sales_ attached to Staff ID. Future updates will include _Response Time_.

| Chart Title          | Visualization Type     | Metric Reference | Notes                                |
| :------------------- | :--------------------- | :--------------- | :----------------------------------- |
| **Top Sales Agents** | Bar Chart (Horizontal) | GMV by Staff     | Filter: Source = Social              |
| **Orders by Agent**  | Table                  | Count of Orders  | Columns: Agent Name, Orders, Revenue |

## Operational Actions

- **Low Social Revenue:**
  - Check if there are unread messages on Facebook Page/Zalo OA.
  - Verify if "Flash Sale" posts have been published.
- **High Traffic / Low Orders:**
  - Audit a random sample of chat logs to check for "missed closing" opportunities.
  - Retrain agents on the current promotion script.

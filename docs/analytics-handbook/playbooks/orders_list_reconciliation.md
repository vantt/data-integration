# Playbook: Orders List Reconciliation

## Overview

- **Audience:** Store Managers, Sales Ops, Data Team
- **Goal:** Verify that orders recorded in the BI system match the source sales system (Sapo). Detect missing, duplicate, or mismatched orders.
- **Metabase Collection:** `Daily Operations`
- **Blueprints:**
  - [Today's Orders](../blueprints/orders_today.md)
  - [Yesterday's Orders](../blueprints/orders_yesterday.md)

## Use Cases

1. **Daily count check:** Compare total order count in BI vs Sapo admin for the same day.
2. **Spot missing orders:** Search by order code — if present in Sapo but absent in BI, ingestion gap detected.
3. **Amount mismatch:** Sort by GMV descending, cross-check large orders with Sapo.
4. **Status reconciliation:** Filter by `payment_status` or `fulfillment_status` to verify status sync.

## Filters

- **Date:** Fixed (Today or Yesterday depending on dashboard).
- **Status:** Filter by order status, payment status, fulfillment status.
- **Channel:** Filter by sales channel.
- **Search:** Search by order code or customer name/phone.

## Data Lineage

- **Core Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
- **Staging (extra fields):** [`stg_sapo_orders`](../../../transformation/models/staging/stg_sapo_orders.sql)
- **Dimensions:** `dim_channels`, `dim_customers`

## Visualizations

### Section 1: Date Label & Summary Count

| Chart Title         | Visualization Type | Notes/Config                                     |
| :------------------ | :----------------- | :----------------------------------------------- |
| **Date**            | Scalar             | Show filtered date (YYYY-MM-DD)                  |
| **Total Orders**    | Scalar             | Quick count for reconciliation                   |
| **Total GMV**       | Scalar             | Sum of GMV for the day                           |

### Section 2: Order Detail Table

| Column             | Source                 | Notes                                              |
| :----------------- | :--------------------- | :------------------------------------------------- |
| **Order Code**     | `stg_sapo_orders`      | Human-readable (e.g. `#1234`). Link to Sapo admin. |
| **Time**           | `fact_orders`          | `HH:MM` format from `order_timestamp`              |
| **Status**         | `fact_orders`          | Color-coded: green=completed, red=cancelled        |
| **Payment Status** | `fact_orders`          | paid / pending / refunded                          |
| **Fulfillment**    | `fact_orders`          | fulfilled / unfulfilled / returned                 |
| **GMV**            | `fact_orders`          | Currency format                                    |
| **Discount**       | `fact_orders`          | Currency format                                    |
| **Channel**        | `dim_channels`         | Sales channel name                                 |
| **Customer**       | `stg_sapo_orders`      | Customer name                                      |
| **Phone**          | `stg_sapo_orders`      | For quick lookup                                   |
| **Payment Method** | `stg_sapo_orders`      | Cash, Card, Transfer, etc.                         |
| **Store**          | `stg_sapo_orders`      | Branch/location name                               |

## Visualization Configs

### Order Detail Table

```json
{
  "display": "table",
  "table.pivot": false,
  "table.column_formatting": [
    { "columns": ["GMV", "Discount"], "type": "currency", "currency": "VND" }
  ]
}
```

## Reconciliation Workflow

1. Open **Today's Orders** (or Yesterday's) dashboard in Metabase.
2. Note the **Total Orders** count and **Total GMV**.
3. Open Sapo Admin > Orders, filter same date.
4. Compare counts. If mismatch > 0, use order code search to identify gaps.
5. For amount mismatches, sort by GMV DESC and spot-check top orders.

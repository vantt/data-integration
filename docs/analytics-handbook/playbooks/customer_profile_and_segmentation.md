# Playbook: Customer Operational Profile

## Overview

- **Audience:** Customer Success, Sales Operations
- **Goal:** View customer lists, demographic profiles, and operational segments (VIP/Loyal).
- **Metabase Collection:** `Customer Operations`

## Data Lineage

- **Core Model:** [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql)
- **Dimensions:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) (for aggregation)

## Filters

- **Created Date:** Date range for new user analysis.
- **Customer Segment:** VIP, Loyal, Regular (Rule-based).
- **Customer Status:** Active, At Risk, Churned.
- **Location:** City, Province.

## Visualizations

### Section 1: Growth & Overview

| Chart Title                 | Visualization Type | Metric Reference                                         | Notes/Config                  |
| :-------------------------- | :----------------- | :------------------------------------------------------- | :---------------------------- |
| **Total Customers**         | Scalar             | Count Distinct `customer_id`                             | All time.                     |
| **New Customers (Monthly)** | Scalar / Trend     | Count `customer_id` where `created_at` = This Month      | Comparison vs Previous Month. |
| **Active Users (MAU)**      | Scalar             | [MAU](../domains/customer.md#4-monthly-active-users-mau) | Users active in last 30 days. |

### Section 2: Segmentation (Operational)

| Chart Title              | Visualization Type | Metric Reference                                       | Notes/Config                                         |
| :----------------------- | :----------------- | :----------------------------------------------------- | :--------------------------------------------------- |
| **Customers by Segment** | Donut Chart        | [Rule-Based RFM](../domains/customer.md#7-rfm-segment) | Group by `customer_segment`.                         |
| **Customers by Status**  | Bar Chart          | [Rule-Based RFM](../domains/customer.md#7-rfm-segment) | Group by `customer_status` (Active/At Risk/Churned). |

### Section 3: Customer List

| Chart Title              | Visualization Type | Columns                                                                 | Notes/Config                                       |
| :----------------------- | :----------------- | :---------------------------------------------------------------------- | :------------------------------------------------- |
| **Customer Detail List** | Table              | Name, Email, Phone, City, **Segment**, **Status**, Last Order Date, LTV | Enable "Click to filter" on Segment/Status charts. |

## Implementation Notes

- **Actionability:** This dashboard is designed for **action**. CS agents should click "At Risk" in the Bar Chart to see the list of customers they need to contact.
- **Exports:** Ensure the "Customer Detail List" is exportable to CSV for email marketing tools.

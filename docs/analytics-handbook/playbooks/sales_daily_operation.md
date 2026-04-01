# Playbook: Daily Sales Operations

## Overview

- **Audience:** Store Managers, Sales Team
- **Goal:** Real-time monitoring of today's sales performance and operational anomalies.
- **Metabase Collection:** `Operations > Daily Monitoring`
- **Blueprint:** [Technical Spec](../blueprints/sales_daily_operation.md)
- **Dashboard:** [Metabase ID 2](/dashboard/2)

## Structure

The dashboard is organized into **4 tabs** for focused analysis:

| Tab | Purpose | Key Questions |
|-----|---------|---------------|
| **Tổng quan** | Quick pulse — KPIs and trends | Revenue, Orders, AOV (with DoD%), Hourly Trend, Cumulative Revenue |
| **Kênh bán hàng** | Channel performance | Revenue/Orders by Channel, Channel vs Yesterday comparison |
| **Sản phẩm** | Product insights | Top products by revenue/quantity, Product Type breakdown |
| **Khách hàng & Thanh toán** | Customer & payment ops | New vs Returning, Order Status, Payment Methods, Discount Impact |

## Data Lineage

- **Core Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — order-level metrics
- **Line Items:** [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql) — product-level metrics
- **Payments:** [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql) — payment method breakdown
- **Dimensions:** `dim_channels`, `dim_products`, `dim_customers`, `dim_payment_methods`

## Tab Details

### Tab 1: Tổng quan (Overview)

The landing tab — designed for a 10-second status check.

**Health Score (top row):**

| Chart Title | Type | Notes |
|-------------|------|-------|
| **Health Score** | Scalar | 0-100 composite score: 75+ Khỏe mạnh, 50-74 Cần chú ý, <50 Báo động |
| **Health Breakdown** | Table | 4 components: Revenue WoW, Orders WoW, Customer Loyalty, AOV Stability |

**KPI Row (scalars):**

| Chart Title | Type | Metric Reference |
|-------------|------|------------------|
| **Net Revenue** | Scalar | [Net Revenue](../domains/sales.md#2-net-revenue) |
| **Total Orders** | Scalar | [Total Orders](../domains/sales.md#4-total-orders) |
| **AOV** | Scalar | [AOV](../domains/sales.md#5-aov-average-order-value) |

**Secondary KPIs:**

| Chart Title | Type | Metric Reference |
|-------------|------|------------------|
| **New Customers** | Scalar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) |
| **Returning Customers** | Scalar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) |
| **Returns** | Scalar | [Return Count](../domains/sales.md#3-return-rate--count) |
| **Discount Rate** | Scalar | [Discount Impact](../domains/sales.md#13-discount-impact) |
| **Total Discounts** | Scalar | [Discount Impact](../domains/sales.md#13-discount-impact) |

**Charts:**

| Chart Title | Type | Notes |
|-------------|------|-------|
| **Hourly Sales Trend** | Line | Today (blue) vs Yesterday (grey) |
| **Cumulative Revenue** | Line | Running total — Today (green) vs Yesterday (grey) |

### Tab 2: Kênh bán hàng (Channels)

| Chart Title | Type | Metric Reference |
|-------------|------|------------------|
| **Revenue by Channel** | Pie | [Sales by Channel](../domains/sales.md#8-sales-by-channel) |
| **Orders by Channel** | Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) |
| **Channel Performance vs Yesterday** | Table | DoD comparison with Revenue Change % |

### Tab 3: Sản phẩm (Products)

| Chart Title | Type | Metric Reference |
|-------------|------|------------------|
| **Top 10 Products by Revenue** | Table | [Top Selling Products](../domains/sales.md#9-top-selling-products) |
| **Top 10 Products by Quantity** | Bar | [Top Selling Products](../domains/sales.md#9-top-selling-products) |
| **Revenue by Product Type** | Pie | Category-level breakdown |
| **Product Performance Table** | Table | Full detail with Qty, Revenue, Avg Price |

### Tab 4: Khách hàng & Thanh toán (Customers & Payments)

**Customer Health (top row):**

| Chart Title | Type | Notes |
|-------------|------|-------|
| **Returning Customer Rate %** | Scalar | Tỷ lệ khách quay lại — red flag nếu giảm dần |
| **At Risk Customers** | Scalar | Tổng khách đang có nguy cơ mất (RFM-based) |

**Detail charts:**

| Chart Title | Type | Metric Reference |
|-------------|------|------------------|
| **New vs Returning Customers** | Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) |
| **Revenue by Customer Segment** | Bar | VIP / Loyal / Regular breakdown |
| **Orders by Status** | Pie | Order status distribution |
| **Payment Method Distribution** | Pie | [Payment Methods](../domains/sales.md#11-payment-method-distribution) |
| **Discount Impact** | Table | [Discount Impact](../domains/sales.md#13-discount-impact) |

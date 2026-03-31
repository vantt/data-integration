# Playbook: CEO Monthly Scorecard

## Overview

- **Audience:** CEO, Co-Founders, Board
- **Goal:** Comprehensive monthly performance review — answer "How did we do this month?" and "What should we change next month?"
- **Cadence:** 1st–3rd of each month, reviewing the closed month.
- **Archetype:** Executive Pulse + Strategic Analysis
- **Metabase Collection:** `Executive` > `Monthly Reports`
- **Related:** [Monthly Business Review Process](./sales_monthly_review.md), [Sales Executive Dashboard](./sales_executive.md)

## Key Questions

1. **Financial Performance:** Có đạt target doanh thu tháng không? Variance bao nhiêu?
2. **Growth Trajectory:** MoM growth bao nhiêu? Trend 6 tháng gần nhất đang lên hay xuống?
3. **Channel Strategy:** Tỷ trọng kênh thay đổi thế nào? Ecommerce vs Offline trend?
4. **Customer Portfolio:** Khách hàng mới bao nhiêu? Bao nhiêu khách At Risk/Churned? Giá trị VIP segment?
5. **Operational Efficiency:** Discount ăn bao nhiêu % doanh thu? Return rate có kiểm soát được không?
6. **Product Mix:** Sản phẩm/brand nào đang drive growth? Sản phẩm nào suy giảm?

## Filters

- **Date Range:** Default = Last Closed Month. Comparison = Previous Month AND Same Month Last Year.
- **No drill-down filters** — full-company view.

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql), [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)
- **Dimensions:** `dim_channels`, `dim_customers`, `dim_products`, `dim_geography`

## Visualizations

### Section 1: Monthly Headline KPIs (Scalar Row)

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Monthly GMV** | Scalar + Trend | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | MoM % change + YoY % change. |
| **Monthly Net Revenue** | Scalar + Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | MoM % change. |
| **Total Orders** | Scalar + Trend | [Total Orders](../domains/sales.md#4-total-orders) | MoM % change. |
| **AOV** | Scalar + Trend | [AOV](../domains/sales.md#5-aov-average-order-value) | MoM % change. |
| **Unique Customers** | Scalar + Trend | _Derived_ | `COUNT(DISTINCT customer_key)` from `fact_orders`. MoM change. |

### Section 2: Target Achievement Scorecard

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Revenue vs Target** | Combo Chart (Bar + Line) | [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate) | Bar: Actual Revenue by week. Line: Cumulative Target. Show achievement %. |
| **Target Variance** | Scalar | [Variance to Target](../domains/sales.md#16-variance-to-target) | Absolute gap. Green if positive, Red if negative. |
| **6-Month Revenue Trend** | Line Chart | [Net Revenue](../domains/sales.md#2-net-revenue) | Monthly aggregation, 6-month window. Show trendline. |

### Section 3: Channel Performance Matrix

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Revenue by Channel Category** | Donut Chart | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Ecommerce / Offline / Internal. Max 5 slices. |
| **Channel Performance Table** | Table (Pivot-style) | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Columns: Channel, Revenue, Orders, AOV, MoM Revenue Change %. Sort by Revenue DESC. |
| **Channel Mix Trend (6M)** | Stacked Area | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Monthly revenue stacked by `channel_category`. Shows structural shift over time. |

### Section 4: Customer Portfolio Health

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **New Customers (MTD)** | Scalar + Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Count with `first_order_date` in this month. MoM change. |
| **Customer Segment Distribution** | Donut Chart | [RFM Segment](../domains/customer.md#7-rfm-segment) | VIP / Loyal / Regular breakdown by customer count. |
| **Revenue by Customer Segment** | Horizontal Bar | [RFM Segment](../domains/customer.md#7-rfm-segment) | Revenue contribution per segment (VIP, Loyal, Regular). |
| **At Risk & Churned Count** | Scalar | [Churn Rate](../domains/customer.md#6-churn-rate) | Count of customers with `customer_status` = At Risk or Churned. Flag if increasing MoM. |

### Section 5: Product & Brand Performance

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Top 10 Products by Revenue** | Table | [Top Selling Products](../domains/sales.md#9-top-selling-products) | Columns: Product Name, Units Sold, Revenue, MoM Change %. From `fact_sales`. |
| **Revenue by Brand** | Horizontal Bar | _Derived from_ [Top Selling Products](../domains/sales.md#9-top-selling-products) | Group by `brand_name` from `dim_products`. |

### Section 6: Operational Efficiency

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Discount Rate %** | Scalar + Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | `Total Discount / GMV × 100`. Flag RED if > 15%. MoM comparison. |
| **Total Discount Amount** | Scalar | [Discount Impact](../domains/sales.md#13-discount-impact) | Absolute VND amount given away. |
| **Return Count** | Scalar + Trend | [Return Rate](../domains/sales.md#3-return-rate--count) | MoM comparison. |
| **Revenue Waterfall** | Table (Waterfall-style) | [Revenue Breakdown](../domains/finance.md#3-revenue-breakdown-waterfall-components) | GMV → Discounts → Returns → Net Revenue. Show each component. |

## Visualization Configs

### Revenue vs Target (Combo)

```json
{
  "display": "combo",
  "graph.dimensions": ["week"],
  "graph.metrics": ["actual_revenue", "cumulative_target"],
  "series_settings": {
    "actual_revenue": { "display": "bar", "color": "#509EE3" },
    "cumulative_target": { "display": "line", "color": "#EF8C8C", "line.style": "dashed" }
  }
}
```

### Channel Mix Trend (Stacked Area)

```json
{
  "display": "area",
  "graph.dimensions": ["month"],
  "graph.metrics": ["revenue"],
  "stackable.stack_type": "stacked",
  "series_settings": {}
}
```

### Customer Segment Distribution (Donut)

```json
{
  "display": "pie",
  "pie.dimension": "customer_segment",
  "pie.metric": "customer_count",
  "pie.show_legend": true,
  "pie.percent_visibility": "inside"
}
```

## Implementation Notes

- **Differs from Sales Executive Dashboard:** This is a **read-only scorecard** with fixed month comparisons. The Sales Executive dashboard has interactive date filters for ad-hoc exploration.
- **Differs from MBR Process:** The [Monthly Business Review](./sales_monthly_review.md) is a **meeting agenda guide**. This playbook is the **dashboard specification** that feeds data into that meeting.
- **Auto-subscription:** Email push on the 2nd of each month at 9:00 AM.
- **Max 15–18 visual elements.** Dense but scannable — CEO reviews once, then delegates follow-ups.

# Playbook: Marketing Monthly Analysis

## Overview

- **Audience:** Marketing Manager, Brand Manager, CMO
- **Goal:** Monthly deep dive into channel effectiveness, customer segments, campaign ROI, and strategic recommendations for next month.
- **Cadence:** 3rd–5th of each month, reviewing the closed month.
- **Archetype:** Exploratory Tool + Executive Pulse
- **Metabase Collection:** `Marketing` > `Monthly Reports`
- **Related:** [Promotion Analysis](./sales_promotion_analysis.md), [Customer Retention](./customer_retention.md)

## Key Questions

1. **Channel Strategy:** Kênh nào đang grow, kênh nào stagnant? Tỷ trọng Ecommerce/Offline thay đổi thế nào trong 6 tháng?
2. **Campaign Effectiveness:** Campaign tháng này ROI bao nhiêu? Discount có ăn hết margin không?
3. **Customer Health:** Cohort retention ra sao? Bao nhiêu khách churn? VIP segment có ổn định không?
4. **Acquisition Efficiency:** Chi phí có khách mới có hợp lý không? Kênh nào mang khách mới tốt nhất?
5. **Brand Portfolio:** Brand nào đang drive growth? Brand nào cần push marketing?

## Filters

- **Date Range:** Default = Last Closed Month. Comparison = Previous Month AND Same Month Last Year.
- **Channel Category:** Ecommerce / Offline / All.
- **Brand (Channel):** Filter by `channel_brand`.
- **Market:** Domestic / Export.

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql), [`fact_marketing_spend`](../../../transformation/models/marts/sales/fact_marketing_spend.sql), [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)
- **Dimensions:** `dim_channels`, `dim_products`, `dim_customers`, `dim_geography`

## Visualizations

### Section 1: Monthly Overview KPIs

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Monthly Revenue** | Scalar + Trend | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | MoM + YoY change. |
| **Total Orders** | Scalar + Trend | [Total Orders](../domains/sales.md#4-total-orders) | MoM change. |
| **New Customers** | Scalar + Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | MoM change. |
| **Discount Rate %** | Scalar | [Discount Impact](../domains/sales.md#13-discount-impact) | Flag RED if > 15%. |

### Section 2: Channel Strategy Analysis

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Channel Mix Trend (6 Months)** | Stacked Area | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Monthly revenue stacked by `channel_category`. Shows structural shifts. |
| **Platform Performance Matrix** | Table | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Columns: Platform, Revenue, Orders, AOV, New Customers, MoM Revenue Change %, MoM Order Change %. Full detail. |
| **Channel Brand Revenue** | Horizontal Bar | _Derived_ | Group by `channel_brand` (JPC, Fine Japan, etc.). Shows brand portfolio split. |
| **Revenue by Market** | Donut Chart | _Derived_ | Domestic vs Export split. From `dim_channels.market`. |
| **Revenue by Customer Segment (B2C/B2B)** | Donut Chart | _Derived_ | From `dim_channels.customer_segment`. |

### Section 3: Customer Acquisition & Retention

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **New Customer Acquisition Trend (6M)** | Bar Chart | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Monthly new customer count. 6-month window. |
| **New Customers by Channel** | Horizontal Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Which channels acquired the most new customers this month? |
| **Customer Segment Movement** | Table | [RFM Segment](../domains/customer.md#7-rfm-segment) | Columns: Segment (VIP/Loyal/Regular), Customer Count, Revenue, MoM Count Change. Shows segment health. |
| **At Risk Customer Alert** | Scalar | [Churn Rate](../domains/customer.md#6-churn-rate) | Count of `customer_status = 'At Risk'`. MoM change. |
| **Cohort Retention Heatmap** | Pivot Table (Heatmap) | [Retention Rate](../domains/customer.md#5-retention-rate) | Month-0 to Month-6 retention by acquisition cohort. Color intensity = retention %. |

### Section 4: Campaign & Promotion Deep Dive

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Promotion Leaderboard** | Table | [Promotion Performance](../domains/sales.md#14-promotion-performance) | Columns: Promo Name, Usage Count, Revenue Generated, Avg Discount %, Uplift (Promo AOV vs Non-Promo AOV). |
| **Discount Depth Distribution** | Histogram (Bar) | [Discount Impact](../domains/sales.md#13-discount-impact) | X: Discount bucket (0%, 10%, 20%…). Y: Order Count. See promotion analysis playbook for SQL. |
| **Discount Trend (6M)** | Line Chart | [Discount Impact](../domains/sales.md#13-discount-impact) | Monthly `Discount Rate %` over 6 months. Goal: keep under 15% line. |
| **Revenue: Discounted vs Full-Price** | Stacked Bar | [Discount Impact](../domains/sales.md#13-discount-impact) | Monthly revenue split: Discounted orders (Orange) vs Full-Price orders (Blue). |

### Section 5: Product & Brand Insights

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Top 15 Products by Revenue** | Table | [Top Selling Products](../domains/sales.md#9-top-selling-products) | Columns: Product, Brand, Units, Revenue, MoM Change %. From `fact_sales`. |
| **Brand Performance Summary** | Table | _Derived_ | Group by `brand_name`. Columns: Brand, Revenue, Units, Order Count, AOV, MoM Growth %. |
| **Brand × Channel Matrix** | Pivot Table | _Derived_ | Rows: Brand. Columns: Channel Category (Ecommerce / Offline). Values: Revenue. Answers "which brands sell where?" |

### Section 6: Geographic Insights

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Revenue by Province (Top 10)** | Horizontal Bar | [Sales by Region](../domains/sales.md#15-sales-by-regionlocation) | From `dim_geography.province` via shipping address. |
| **Order Heatmap by Day × Hour** | Heatmap | [Hourly Heatmap](../domains/sales.md#7-hourly-heatmap-day-of-week-analysis) | Identifies peak ordering windows for marketing scheduling. |

## Visualization Configs

### Cohort Retention Heatmap

```json
{
  "display": "pivot",
  "pivot.show_column_totals": false,
  "pivot.show_row_totals": false,
  "table.column_formatting": [{
    "columns": ["retention_rate"],
    "type": "range",
    "colors": ["#FFFFFF", "#509EE3"],
    "min_type": "custom",
    "min_value": 0,
    "max_type": "custom",
    "max_value": 100
  }]
}
```

### Channel Mix Trend (Stacked Area)

```json
{
  "display": "area",
  "stackable.stack_type": "stacked",
  "graph.dimensions": ["month"],
  "graph.metrics": ["revenue"],
  "series_settings": {}
}
```

## Operational Actions

- **Channel Declining 2+ Consecutive Months:** Schedule strategy review. Consider reallocating marketing spend.
- **New Customer Acquisition Declining:** Audit ad spend, review landing page conversion, check competitor activity.
- **Churn Increasing:** Trigger reactivation campaign for At Risk segment. Review product quality/pricing.
- **Discount Rate > 15%:** Review active promotions. Propose tighter discount guardrails for next month.
- **Brand Under-performing:** Cross-reference with inventory — is it a supply issue or demand issue?

## Implementation Notes

- **Differs from CEO Monthly Scorecard:** This dashboard is **much deeper** — includes cohort analysis, promotion drill-down, brand × channel matrix, and geographic data. CEO version is a summary.
- **Differs from Promotion Analysis Playbook:** The [Promotion Analysis](./sales_promotion_analysis.md) is an **ad-hoc deep dive tool**. This playbook includes promotion as ONE section of a broader monthly review.
- **Data Dependency:** Cohort retention and segment movement require `dim_customers` with accurate `first_order_date` and `customer_status`. Verify data freshness.
- Max ~20 visual elements. Marketing Manager will spend 15–30 minutes reviewing.

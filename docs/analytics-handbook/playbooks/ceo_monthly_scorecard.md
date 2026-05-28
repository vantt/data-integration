# Playbook: CEO Monthly Scorecard

## Overview

- **Audience:** CEO, Co-Founders, Board
- **Goal:** Comprehensive monthly performance review — answer "How did we do this month?" and "What should we change next month?"
- **Cadence:** 1st–3rd of each month, reviewing the closed month.
- **Archetype:** Executive Pulse (multi-view — 3 tabs)
- **Collection:** `Executive`
- **Design Spec:** [CEO Monthly Scorecard](../designs/ceo_monthly_scorecard.md)
- **Related:** [Monthly Business Review Process](./sales_monthly_review.md)

## Key Questions

1. **Financial Performance:** Có đạt target doanh thu tháng không? Variance bao nhiêu?
2. **Growth Trajectory:** MoM growth bao nhiêu? Trend 6 tháng gần nhất đang lên hay xuống?
3. **Channel Strategy:** Tỷ trọng kênh thay đổi thế nào? Ecommerce vs Offline trend?
4. **Customer Portfolio:** Khách hàng mới bao nhiêu? Bao nhiêu khách At Risk/Churned? Giá trị VALUE_VIP segment?
5. **Operational Efficiency:** Discount ăn bao nhiêu % doanh thu? Return rate có kiểm soát được không?
6. **Product Mix:** Sản phẩm/brand nào đang drive growth? Sản phẩm nào suy giảm?

## Filters

- **Date Range:** Default = Last Closed Month. Comparison = Previous Month (MoM).
- **No drill-down filters** — full-company view, zero-interaction.

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql), [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)
- **Dimensions:** `dim_channels`, `dim_customers`, `dim_products`

## Dashboard Structure (3 Tabs)

### Tab 1: Hiệu suất tháng

Focus: The big picture — "Tháng vừa rồi thế nào?"

| Chart Title | Visualization Type | Metric Reference | Notes |
| :--- | :--- | :--- | :--- |
| **Monthly Net Revenue** | Scalar + MoM Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | Hero metric. MoM % change. |
| **Monthly GMV** | Scalar + MoM Trend | [GMV](../domains/sales.md#1-gross-revenue-gmv) | MoM % change. |
| **Total Orders** | Scalar + MoM Trend | [Total Orders](../domains/sales.md#4-total-orders) | MoM % change. |
| **AOV** | Scalar + MoM Trend | [AOV](../domains/sales.md#5-aov-average-order-value) | MoM % change. |
| **Unique Customers** | Scalar + MoM Trend | _Derived_ | MoM change. |
| **Target Achievement** | Progress Bar | [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate) | Actual vs monthly target. |
| **Target Variance** | Scalar | [Variance to Target](../domains/sales.md#16-variance-to-target) | Absolute gap. |
| **Revenue vs Target (Weekly)** | Combo Chart (Bar + Line) | [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate) | Bar: Weekly actual. Line: Monthly target (dashed). |
| **6-Month Revenue Trend** | Multi-line Chart | [Net Revenue](../domains/sales.md#2-net-revenue) | Gross + Net Revenue, 6-month window. |
| **Revenue Waterfall** | Waterfall Chart | [Revenue Breakdown](../domains/finance.md#3-revenue-breakdown-waterfall-components) | GMV → Discounts → Returns → Net Revenue. |

### Tab 2: Kênh & Khách hàng

Focus: "Điều gì đang drive growth? Khách hàng ra sao?"

| Chart Title | Visualization Type | Metric Reference | Notes |
| :--- | :--- | :--- | :--- |
| **Revenue by Channel Category** | Donut Chart | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Online-Ecommerce / Offline / Internal. Max 3 slices. |
| **Channel Performance Table** | Table + Conditional Formatting | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Revenue, Orders, AOV, MoM %. Green/Red conditional on MoM. |
| **Channel Mix Trend (6M)** | Stacked Area | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Monthly revenue stacked by channel_category. |
| **New Customers** | Scalar + MoM Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | MoM change. |
| **At Risk Customers** | Scalar | [Churn Rate](../domains/customer.md#6-churn-rate) | ⚠ prefix. |
| **Churned Customers** | Scalar | [Churn Rate](../domains/customer.md#6-churn-rate) | — |
| **Customer Segment Distribution** | Donut Chart | [Value Group](../domains/customer.md#7-rfm-segment) | VALUE_VIP / GOLD / SILVER / BRONZE breakdown. |
| **Revenue by Customer Segment** | Horizontal Bar | [Value Group](../domains/customer.md#7-rfm-segment) | Revenue contribution per segment. |

### Tab 3: Sản phẩm & Vận hành

Focus: "Product mix + operational health"

| Chart Title | Visualization Type | Metric Reference | Notes |
| :--- | :--- | :--- | :--- |
| **Top 10 Products by Revenue** | Table + Conditional Formatting | [Top Selling Products](../domains/sales.md#9-top-selling-products) | Product, Brand, Units, Revenue, MoM %. Green/Red on MoM. |
| **Revenue by Brand** | Horizontal Bar | _Derived from_ [Top Selling Products](../domains/sales.md#9-top-selling-products) | Top 10 brands by revenue. |
| **Discount Rate %** | Scalar + MoM Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | Flag RED if > 15%. |
| **Total Discount Amount** | Scalar | [Discount Impact](../domains/sales.md#13-discount-impact) | Absolute VND. |
| **Return Count** | Scalar + MoM Trend | [Return Rate](../domains/sales.md#3-return-rate--count) | MoM comparison. |
| **Revenue Breakdown Table** | Table | [Revenue Breakdown](../domains/finance.md#3-revenue-breakdown-waterfall-components) | GMV → Discounts → Returns → Net. Detailed table companion. |

### Monthly Profitability

Focus: "Tháng vừa rồi lợi nhuận thế nào? Chi phí đang ăn mòn margin ở đâu?"

Added to Tab 1 (Hiệu suất tháng) below Revenue Waterfall section.

| Chart Title | Visualization Type | Metric Reference | Notes |
| :--- | :--- | :--- | :--- |
| **Monthly Gross Margin %** | Scalar + target + MoM | [Gross Margin](../domains/finance.md#5-gross-margin) | Target=40%. Data from `fact_order_economics`. COALESCE/NULLIF protect divide-by-zero. |
| **Channel Profitability Breakdown** | Grouped Bar (channel × profit MoM) | [Channel Net Profit](../domains/finance.md#6-channel-net-profit) | This month vs last month net_profit per channel. FULL OUTER JOIN handles new/exited channels. |
| **Cost Structure Breakdown** | Horizontal Bar (% of Net Revenue) | [Cost Structure](../domains/finance.md#10-cost-structure) | From `fact_order_costs` long-format. Categories: COGS, PLATFORM_FEE, TAX, SHIPPING. May return sparse data if `fact_order_costs` partially populated. |

**Data sources**: `fact_order_economics` (metrics #5, #6) + `fact_order_costs` (metric #10).

**Filter applied**: `is_sales_channel = true`, `status NOT IN ('CANCELLED', 'Voided')`, window = last closed month.

## Implementation Notes

- **3-tab structure**: Each tab is self-contained with its own narrative flow. CEO can review Tab 1 only (3 min) or go deeper into Tabs 2-3.
- **All KPIs have MoM comparison**: Every scalar shows trend arrow with vs tháng trước.
- **Waterfall chart**: Waterfall visualization for revenue decomposition (GMV → Net).
- **Conditional formatting**: Channel table and Product table highlight positive/negative MoM changes.
- **Auto-subscription:** Email push on the 2nd of each month at 9:00 AM.
- **Max ~25 cards across 3 tabs** — ~10 per tab, scannable within time budget.

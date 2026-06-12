# Playbook: Marketing Monthly Analysis

## Overview

- **Audience:** Marketing Manager, Brand Manager, CMO
- **Goal:** Monthly deep dive into channel effectiveness, customer segments, promotion analysis, and strategic recommendations for next month.
- **Cadence:** 3rd–5th of each month, reviewing the closed month.
- **Archetype:** Operational Cockpit (multi-view, 4 tabs)
- **Collection:** `Marketing & Customers`
- **Related:** [Promotion Analysis](./sales_promotion_analysis.md), [Customer Retention & Cohorts](../blueprints/customer_retention_cohorts.md)
- **Design Spec:** [Marketing Monthly Analysis Design](../designs/marketing_monthly_analysis.md)

## Key Questions

1. **Channel Strategy:** Kênh nào đang grow, kênh nào stagnant? Tỷ trọng Ecommerce/Offline thay đổi thế nào trong 6 tháng?
2. **Campaign Effectiveness:** Discount có ăn hết margin không? Promotion nào hiệu quả?
3. **Customer Health:** Cohort retention ra sao? Bao nhiêu khách churn? VALUE_VIP segment có ổn định không?
4. **Brand Portfolio:** Brand nào đang drive growth? Brand nào cần push marketing?

## Filters

> Filters removed — DuckDB native SQL template tags do not support `date/all-options` or `string/=` filter types. Date scoping is hardcoded in each query (last closed month).

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql), [`fact_order_economics`](../../../transformation/models/marts/finance/fact_order_economics.sql), [`fact_marketing_spend`](../../../transformation/models/marts/marketing/fact_marketing_spend.sql)
- **Dimensions:** `dim_channels`, `dim_products`, `dim_customers`, `dim_promotions`, `dim_geography`

## Dashboard Structure (5 Tabs)

1. **Monthly Pulse** — Executive-level monthly snapshot (5-7 min). Hero revenue + KPIs + discount gauge + 6M trends + channel mix.
2. **Channel & Brand** — Channel deep dive: mix trends, platform matrix, brand portfolio, market/segment splits.
3. **Customer Intelligence** — Acquisition trends, channel attribution, segment health, cohort retention heatmap, at-risk/churn alerts.
4. **Campaigns & Products** — Discount analysis, promotion leaderboard, top products, geographic insights, ordering patterns.
5. **ROI & Margin** — Marketing P&L: ROAS + margin by channel, channel profit contribution vs spend. Retail scope, last-click attribution.

## Visualizations

### Tab 1: Monthly Pulse

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Monthly Net Revenue** | Scalar + MoM Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | MoM % change. |
| **Monthly Total Orders** | Scalar + MoM Trend | [Total Orders](../domains/sales.md#4-total-orders) | MoM % change. |
| **Monthly New Customers** | Scalar + MoM Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | MoM % change. From `dim_customers.first_order_date`. |
| **Monthly AOV** | Scalar + MoM Trend | [AOV](../domains/sales.md#5-aov-average-order-value) | MoM % change. |
| **Discount Rate Gauge** | Gauge | [Discount Impact](../domains/sales.md#13-discount-impact) | Zones: Green 0-10%, Yellow 10-15%, Red 15%+. |
| **Revenue Trend (6M)** | Line Chart | [Net Revenue](../domains/sales.md#2-net-revenue) | Monthly net revenue, 6-month window. |
| **Channel Revenue Share** | Donut | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Online-Ecommerce / Offline split. Max 3 slices. |
| **Revenue by Channel (MoM)** | Multi-Line | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | 6-month trend, one line per channel_category. |

### Tab 2: Channel & Brand

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Channel Mix Trend (6M)** | Stacked Area | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Monthly revenue stacked by `channel_category`. Shows structural shifts. |
| **Platform Performance Matrix** | Table | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Columns: Platform, Revenue, Orders, AOV, New Customers, MoM Revenue %, MoM Orders %. |
| **Channel Brand Revenue** | Horizontal Bar | _Derived_ | Group by `channel_brand` (JPC, Fine Japan, etc.). |
| **Revenue by Market** | Donut Chart | _Derived_ | Domestic vs Export split. From `dim_channels.market`. |
| **Brand Performance Summary** | Table | _Derived_ | Brand, This Month Revenue/Units, Last Month Revenue/Units, MoM Growth %. From `fact_sales`. |
| **Revenue by Customer Segment (B2C/B2B)** | Donut Chart | _Derived_ | From `source_type`. |

### Tab 3: Customer Intelligence

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **New Customers (Month)** | Scalar + MoM Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | From `dim_customers.first_order_date`. |
| **Returning Customers (Month)** | Scalar + MoM Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Customers with orders this month who are not new. |
| **New Customer Revenue Share** | Scalar + MoM Trend | _Derived_ | Revenue from first-time buyers as % of total. |
| **New Customer Acquisition Trend (6M)** | Bar Chart | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Monthly new customer count, 6-month window. |
| **New Customers by Channel** | Horizontal Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Which channels acquired the most new customers this month? |
| **At Risk Customers** | Scalar + MoM Trend | [Churn Rate](../domains/customer.md#6-churn-rate) | Count of `customer_status = 'At Risk'`. MoM change. |
| **Churn Rate Gauge** | Gauge | [Churn Rate](../domains/customer.md#6-churn-rate) | Zones: Green 0-10%, Yellow 10-20%, Red 20%+. |
| **Active Customer Rate** | Scalar + MoM Trend | _Derived_ | Active / total customers %. |
| **Customer Value Group Movement** | Table | [Value Group](../domains/customer.md#7-rfm-segment) | Segment, Customer Count, Revenue, MoM Count Change. |
| **Cohort Retention Heatmap** | Pivot Table (Heatmap) | [Retention Rate](../domains/customer.md#5-retention-rate) | Month-0 to Month-6 retention by acquisition cohort. Color intensity = retention %. |

### Tab 4: Campaigns & Products

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Total Discount Amount** | Scalar + MoM Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | Absolute VND discounted. MoM change. |
| **Discounted Order Percentage** | Scalar + MoM Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | % of orders with discount. |
| **Average Discount Depth** | Scalar + MoM Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | Avg discount % per discounted order. |
| **Promotion Leaderboard** | Table | [Promotion Performance](../domains/sales.md#14-promotion-performance) | Columns: Promo Code, Usage, Revenue, Avg Discount %, Promo AOV, Non-Promo AOV. Top 10. |
| **Discount Trend (6M)** | Line Chart | [Discount Impact](../domains/sales.md#13-discount-impact) | Monthly Discount Rate % over 6 months. 15% goal line. |
| **Revenue: Discounted vs Full-Price (6M)** | Stacked Bar | [Discount Impact](../domains/sales.md#13-discount-impact) | Monthly revenue split: Discounted (Orange) vs Full-Price (Blue). |
| **Top 15 Products by Revenue** | Table | [Top Selling Products](../domains/sales.md#9-top-selling-products) | Product, Brand, This Month Units/Revenue, Last Month Units/Revenue, MoM %. From `fact_sales`. |
| **Revenue by Province (Top 10)** | Horizontal Bar | [Sales by Region](../domains/sales.md#15-sales-by-regionlocation) | From `dim_geography.province` via shipping address. |
| **Order Heatmap — Day × Hour** | Heatmap | [Hourly Heatmap](../domains/sales.md#7-hourly-heatmap-day-of-week-analysis) | Peak ordering windows for marketing scheduling. |

### Tab 5: Marketing P&L

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **ROAS + Margin by Channel** | Table | [Finance #5 Net Profit](../domains/finance.md#5-net-profit), [Finance #6 Gross Margin](../domains/finance.md#6-gross-margin), [Finance #10 Channel P&L](../domains/finance.md#10-channel-pl) | Columns: Channel, Spend, Attributed Revenue, ROAS, Margin %, Profitable ROAS (=ROAS×margin%), Spend MoM %. Conditional formatting: Margin % green ≥30%, red <10%; ROAS green ≥3, red <1. Retail scope. |
| **Channel Profit Contribution vs Spend** | Combo Chart | [Finance #5 Net Profit](../domains/finance.md#5-net-profit), [Finance #10 Channel P&L](../domains/finance.md#10-channel-pl) | Bar = Spend (this month), Line = Net Profit (this month). Retail scope. Last closed month vs prior month. |

> **Attribution caveat:** All metrics use last-click attribution via `channel_key` match between `fact_marketing_spend` and `fact_order_economics`. ROAS = attributed_revenue / spend. Profitable ROAS = ROAS × margin%. CAC analysis pending (acquisition_source NULL in Sapo).

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

- **Channel Declining 2+ Consecutive Months:** Schedule strategy review.
- **New Customer Acquisition Declining:** Audit ad spend, review landing page conversion, check competitor activity.
- **Churn Increasing:** Trigger reactivation campaign for At Risk segment. Review product quality/pricing.
- **Discount Rate > 15%:** Review active promotions. Propose tighter discount guardrails for next month.
- **Brand Under-performing:** Cross-reference with inventory — supply issue or demand issue?

## Implementation Notes

- **Differs from CEO Monthly Scorecard:** This dashboard is **much deeper** — includes cohort analysis, promotion drill-down, brand performance, and geographic data. CEO version is a summary.
- **Differs from Promotion Analysis Playbook:** The [Promotion Analysis](./sales_promotion_analysis.md) is an **ad-hoc deep dive tool**. This playbook includes promotion as ONE section of a broader monthly review.
- **No interactive filters** — DuckDB native SQL template tags don't support Metabase filter types. Date scoping hardcoded in SQL.
- **Data Dependency:** Cohort retention and segment movement require `dim_customers` with accurate `first_order_date` and `customer_status`. Verify data freshness.
- Max ~30 visual elements across 4 tabs. Marketing Manager will spend 15–30 minutes reviewing.

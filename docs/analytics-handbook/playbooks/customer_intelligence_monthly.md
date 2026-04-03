# Playbook: Customer Intelligence Monthly

## Overview

- **Audience:** CEO, Marketing Manager, Sales Ops
- **Goal:** Monthly deep-dive into customer health, value concentration, segment dynamics, purchase behavior, and acquisition quality.
- **Collection:** `Marketing & Customers`
- **Cadence:** Monthly review (first week of each month), 15-20 min working session
- **Design Spec:** [Customer Intelligence Monthly](../designs/customer_intelligence_monthly.md)

## Data Lineage

- **Core Model:** [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql) — customer attributes, RFM segmentation, lifecycle status
- **Fact Tables:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql)
- **Dimensions:** `dim_channels`, `dim_products`

## Filters

- **Segment:** VIP, Loyal, Regular (multi-select) — applies to Tab 2 and Tab 3

## Dashboard Structure (3 Tabs)

### Tab 1: Overview & Health

> **Blueprint:** [Customer Intelligence Monthly](../blueprints/customer_intelligence_monthly.md)

**Purpose:** Quick pulse check — "How healthy is our customer base this month?"

| Chart Title | Viz Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Total Customers** | Scalar (Hero) | [Total Customers](../domains/customer.md) | Customers with 1+ orders, MoM trend |
| **Active Customers (30d)** | Scalar | [MAU](../domains/customer.md#4-monthly-active-users-mau) | Active in last 30 days, MoM trend |
| **New Customers (Last Month)** | Scalar | Derived from `created_at` | Monthly acquisition volume, MoM trend |
| **One-Time Buyer Rate** | Scalar | % with only 1 order | Conversion opportunity signal, MoM trend |
| **Customer Status Distribution** | Donut | Active / At Risk / Churned | Part-to-whole status view |
| **Customer Segment Distribution** | Donut | VIP / Loyal / Regular | Part-to-whole segment sizes |
| **Revenue from Top 20% Customers** | Scalar | Pareto indicator | Revenue concentration % |
| **Monthly Acquisition vs Churn (6M)** | Combo | Acquired bar + Churned bar + Net Growth line | Net customer growth momentum |
| **Customer Health Scorecard** | Table | Per-segment vitals | Active%, At Risk%, Churned%, Repeat%, Avg LTV, Avg Orders, Avg Recency — conditional formatting |

### Tab 2: Value & Segmentation

**Purpose:** Answer "Where is our revenue concentrated and how are segments performing?"

| Chart Title | Viz Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Total Customer LTV** | Scalar (Hero) | Sum of `lifetime_value` | Cumulative LTV, MoM trend |
| **Avg LTV per Customer** | Scalar | Avg `lifetime_value` | MoM trend |
| **Avg Orders per Customer** | Scalar | Avg `total_orders_count` | Purchase frequency, MoM trend |
| **Repeat Purchase Rate** | Scalar | [Retention Rate](../domains/customer.md#5-retention-rate) | % with >1 order, MoM trend |
| **Customer Value Distribution** | Bar (histogram) | LTV range buckets | Shape of customer value base (0, <500K, 500K-1M, 1M-2M, 2M-5M, 5M-10M, 10M+) |
| **Segment Revenue Share** | Donut | Revenue by VIP / Loyal / Regular | Revenue concentration by segment |
| **AOV by Segment Trend (6M)** | Multi-line | AOV per segment monthly | Spending trajectory per segment |
| **Revenue by Segment Trend (6M)** | Stacked Area | Revenue by segment monthly | Which segments grow over time |
| **Segment Revenue & Metrics Detail** | Table | Per-segment: Customers, Revenue, Revenue%, Avg LTV, Avg Orders, Avg Recency | Ranked by revenue, conditional formatting on Revenue% and Avg Recency |

### Tab 3: Behavior & Insights

**Purpose:** Answer "What are customers buying and through which channels?"

| Chart Title | Viz Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Channel Revenue by Segment** | Stacked Bar | Revenue by channel x segment (last 3M) | Which channels drive revenue per segment |
| **Top 10 Products — VIP Customers** | Horizontal Bar | Revenue by product (last 3M) | VIP product preferences — guide retention offers |
| **Top 10 Products — First-Time Buyers** | Horizontal Bar | Revenue by product (last 3M) | Entry products — guide acquisition funnels |
| **New Customer Quality Trend (6M)** | Combo | New Customers bar + Avg First Order line + 30d Repeat % line | Cohort quality: volume, first AOV, early repeat rate |
| **Loyalty Point Distribution by Segment** | Stacked Bar | Points buckets by segment | Loyalty engagement level per segment |
| **Gender Distribution by Segment** | Stacked Bar | Gender by segment | Demographic mix for persona targeting |

## How to Read This Dashboard

1. **Start with Tab 1** — KPI row tells total customers, active rate, new customers, and one-time buyer rate vs last month. Green = improving, red = declining. If one-time buyer rate is rising, conversion programs need attention.
2. **Check growth dynamics** — Acquisition vs Churn combo chart shows net growth momentum. If churned bars exceed acquired bars, escalate immediately. Health scorecard breaks down each segment's vitals with conditional alerts.
3. **Move to Tab 2** — Identify where value concentrates. Top 20% revenue share (from Tab 1) plus segment revenue donut show Pareto risk. AOV trends reveal if spending is increasing or eroding per segment. The detail table ranks segments by revenue contribution.
4. **Use Tab 3 for action** — Channel revenue by segment guides channel investment. Product affinity charts (VIP vs first-time) inform retention offers and acquisition funnels. New customer quality trend flags whether recent cohorts convert and repeat well. Demographics and loyalty data support persona-level targeting.

## Key Metrics Reference

| Metric | Definition | Source | Threshold |
|--------|-----------|--------|-----------|
| One-Time Buyer Rate | % of customers with exactly 1 order | dim_customers | Rising = conversion risk |
| Top 20% Revenue Share | % of total revenue from top quintile | dim_customers | High concentration = dependency risk |
| Active | recency_days <= 30 | dim_customers | — |
| At Risk | recency_days 31-90 | dim_customers | Escalate if trending up |
| Churned | recency_days > 90 | dim_customers | — |
| Repeat Purchase Rate | % customers with >1 order | dim_customers | Higher = healthier base |

## Implementation Notes

- **Business Constraints:** Excludes `customer_id = 'Unknown'`, cancelled/voided orders, and zero-order customers
- **Comparison Frame:** MoM for KPIs, 6-month trend for patterns, 3-month window for channel/product analysis
- **Design Spec:** [designs/customer_intelligence_monthly.md](../designs/customer_intelligence_monthly.md)
- **Blueprint:** [blueprints/customer_intelligence_monthly.md](../blueprints/customer_intelligence_monthly.md)
- **Domain Reference:** [domains/customer.md](../domains/customer.md)

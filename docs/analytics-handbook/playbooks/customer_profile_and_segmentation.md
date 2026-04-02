# Playbook: Customer Intelligence Monthly

## Overview

- **Audience:** CEO, Marketing Manager, Sales Ops
- **Goal:** Monthly deep-dive into customer health, value concentration, segment dynamics, purchase behavior, and acquisition quality.
- **Collection:** `Marketing & Customers`
- **Cadence:** Monthly review (first week of each month)

## Data Lineage

- **Core Model:** [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql)
- **Fact Tables:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql)
- **Dimensions:** `dim_channels`, `dim_products`

## Dashboard Structure (3 Tabs)

### Tab 1: Overview & Health
- **Purpose:** Answer "How healthy is our customer base this month?"
- **Hero:** Total Customers with MoM trend
- **Key visuals:** KPI row with MoM comparisons, customer status donut, health scorecard with conditional formatting, acquisition vs churn trend

### Tab 2: Value & Segmentation
- **Purpose:** Answer "Where is our revenue concentrated and how are segments performing?"
- **Key visuals:** LTV distribution histogram, segment revenue donut, AOV by segment trend, segment migration indicators

### Tab 3: Behavior & Insights
- **Purpose:** Answer "What are customers buying and through which channels?"
- **Key visuals:** Channel preference by segment, top products by VIP vs first-time buyers, new customer quality cohort trend, demographics

## How to Read

1. **CONTEXT** — This dashboard exists to monitor customer base health monthly and detect early signals of value erosion or growth opportunities.
2. **KEY FINDING** — Start with Tab 1: the KPI row tells you total customers, active rate, and one-time buyer rate vs last month. Red = declining, green = improving.
3. **EVIDENCE** — The acquisition vs churn chart shows net growth momentum. The health scorecard breaks down each segment's vitals.
4. **IMPLICATIONS** — If one-time buyer rate is rising, conversion programs need attention. If VIP churn increases, escalate to retention team.
5. **ACTIONS** — Use Tab 2 to identify which segments need intervention. Use Tab 3 to understand what products and channels drive different segments.

## Implementation Notes

- **Design Spec:** [designs/customer_intelligence_monthly.md](../designs/customer_intelligence_monthly.md)
- **Blueprint:** [blueprints/customer_intelligence_monthly.md](../blueprints/customer_intelligence_monthly.md)
- **Domain Reference:** [domains/customer.md](../domains/customer.md)

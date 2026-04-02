# Playbook: Customer Retention & Lifecycle

## Overview

- **Audience:** Marketing Manager, Customer Success, CEO
- **Goal:** Track retention health, analyze cohort behavior, identify churn risks, and measure reactivation success.
- **Cadence:** Monthly review (first week), with bi-weekly check on Tab 1
- **Collection:** `Marketing & Customers`
- **Design Spec:** [Customer Retention & Lifecycle](../designs/customer_retention_lifecycle.md)

## Data Lineage

- **Core Models:**
  - [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql) — customer attributes, RFM segmentation, lifecycle status
  - [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — order transactions for cohort analysis

## Filters

- **Customer Segment:** VIP, Loyal, Regular (multi-select)

## Dashboard Structure (3 Tabs)

### Tab 1: Suc khoe Retention

> **Blueprint:** [Customer Retention Dashboard](../blueprints/customer_retention_dashboard.md)

**Purpose:** Quick pulse check — are we retaining better or worse than last month?

| Chart Title | Viz Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Repeat Purchase Rate** | Scalar (Hero) | [Retention Rate](../domains/customer.md#5-retention-rate) | % with >1 order, MoM trend |
| **Churn Rate** | Scalar | [Churn Rate](../domains/customer.md#6-churn-rate) | 90+ days inactive, MoM trend |
| **Avg Customer Lifespan** | Scalar | Derived from `lifespan_days` | Days between first/last order |
| **Active Customer Rate** | Scalar | [MAU](../domains/customer.md#4-monthly-active-users-mau) | % active in last 30 days |
| **Customer Lifecycle Distribution** | Donut | Active/At Risk/Churned | Part-to-whole status view |
| **Revenue by Lifecycle Status** | Bar | Revenue by status | Where is revenue concentrated |
| **Segment x Status Matrix** | Stacked Bar | Status by segment | Which segments churn most |
| **Churn Rate Trend (6M)** | Line | Churn Rate monthly | With target line |
| **Repeat Purchase Rate Trend (6M)** | Line | Repeat % monthly | Retention trajectory |
| **Retention Health Scorecard** | Table | Per-segment vitals | Conditional formatting |

### Tab 2: Phan tich Cohort

**Purpose:** Deep-dive into acquisition cohort retention and revenue contribution patterns.

| Chart Title | Viz Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Avg Month-1 Retention** | Scalar (Hero) | Cohort M1 retention avg | Early lifecycle health |
| **Best Cohort (M1 Retention)** | Scalar | Top performing cohort | Highlight best month |
| **Avg Orders per Customer** | Scalar | Frequency | MoM trend |
| **New vs Returning Revenue Ratio** | Scalar | Revenue split | % from returning |
| **Cohort Retention Heatmap** | Pivot Table | Cohort retention matrix | 12-month lookback |
| **Revenue by Cohort (Layer Cake)** | Stacked Area | Revenue by acquisition cohort | Shows legacy vs new contribution |
| **New vs Returning Revenue (6M)** | Stacked Area | Revenue by customer type | Dependency analysis |
| **New vs Returning Customer Count (6M)** | Stacked Bar | Customer counts by type | Volume comparison |

### Tab 3: Hanh vi & Reactivation

**Purpose:** Understand buying patterns and measure win-back campaign effectiveness.

| Chart Title | Viz Type | Metric Reference | Notes |
|:---|:---|:---|:---|
| **Avg Days Between Purchases** | Scalar (Hero) | Inter-purchase gap | Campaign timing signal |
| **Reactivated Customers** | Scalar | Win-back count | MoM trend |
| **At-Risk Customers** | Scalar | Count of At Risk status | Action required |
| **One-Time Buyer Rate** | Scalar | % single-order customers | Conversion opportunity |
| **Purchase Frequency Distribution** | Bar | Order count histogram | One-time vs repeat shape |
| **Days Between Purchases Distribution** | Bar | Gap histogram | Optimal nudge timing |
| **Reactivation Trend (6M)** | Combo | Reactivated count + revenue | Win-back effectiveness |
| **At-Risk Customer Watchlist** | Table | Customer details | Sorted by LTV DESC |

## How to Read This Dashboard

1. **Start with Tab 1** — Check Repeat Purchase Rate (hero). If declining MoM, investigate churn sources in the lifecycle distribution and scorecard.
2. **Move to Tab 2** — If retention is declining, check cohort heatmap to see if recent cohorts retain worse or if it's a systemic issue. Layer cake shows if revenue depends too heavily on new customers.
3. **Use Tab 3** — For campaign planning: purchase gap distribution tells you when to send reactivation nudges. The watchlist is your immediate action item for high-value at-risk customers.

## Implementation Notes

- **Cohort Logic:** Uses `first_order_date` truncated to month as cohort identifier
- **Churn Definition:** 90+ days since last purchase (from `customer_status` in dim_customers)
- **At Risk Definition:** 31-90 days since last purchase
- **Reactivation:** Customer who returned after 30+ day gap from previous order

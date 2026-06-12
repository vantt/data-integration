# Playbook: Weekly · Customer Retention & Cohorts [Retail]

## Overview

- **Audience:** Marketing Manager, Customer Success
- **Goal:** Answer "are retail customers coming back?" — track repeat rate, churn, and lifecycle health; analyze cohort retention patterns; measure reactivation effectiveness.
- **Tool:** metabase
- **Collection:** `Marketing & Customers › 👥 Customer`
- **Cadence:** Weekly review; full cohort analysis monthly
- **Scope:** scope_retail (`customer_type = 'RETAIL'`) — WHOLESALE/PARTNER/STAFF excluded
- **Blueprint:** [`../blueprints/metabase/customer_retention_cohorts.md`](../blueprints/metabase/customer_retention_cohorts.md)

> **Note:** This board is analytics-only. Operational call lists and at-risk watchlists live in the **Daily Action Queue** board — do not duplicate actionable queues here.

## Data Lineage

- **`mart_retention_waterfall_monthly`** — point-in-time lifecycle status counts per snapshot month. Replaces survivorship-biased `mart_customer_status_snapshot_monthly` for trend views; use this for ACTIVE/AT_RISK/CHURNED trend charts.
- **`mart_customer_status_snapshot_monthly`** — month-end snapshots for scalar MoM comparisons (Repeat Rate, Churn Rate, One-Time Rate).
- **`fact_orders`** — order transactions for cohort retention, layer cake, new vs returning splits.
- **`dim_customers`** — customer attributes: `customer_status`, `value_group`, `order_count`, `lifetime_value`, `first_order_date`, `avg_days_between_orders`.

**Cohort logic:** acquisition cohort = `first_order_date` truncated to month. M0 = acquisition month (always 100%). M1–M11 = subsequent months.

**Status definitions:**
- Active: last purchase ≤ 30 days
- At Risk: 31–90 days since last purchase
- Churned: > 90 days since last purchase
- Reactivated: returned after 30+ day gap from prior order

## Reading Flow

### Tab 1 — Sức khỏe Retention

**Purpose:** Quick pulse — are we retaining better or worse than last period?

1. Check hero scalars (Repeat Purchase Rate, Churn Rate, Active Customer Rate, Avg Order Value) with MoM delta.
2. Lifecycle distribution donut → where is the customer base concentrating (Active / At Risk / Churned)?
3. Retention waterfall trend (6M stacked area) → point-in-time view free of survivorship bias.
4. Repeat Purchase Rate trend line → is retention trajectory improving?
5. Retention Health Scorecard table → per-segment vitals with conditional formatting; flag segments where Churned% is rising.
6. MAU vs Repeat-Buyer MAU (12M dual-line) → narrowing gap = improving engagement quality.

### Tab 2 — Phân tích Cohort

**Purpose:** Are recent acquisition cohorts retaining as well as older ones?

1. Check scalars: Avg M1 Retention (early lifecycle health), Best Cohort, Avg Orders per Customer, Returning Revenue Ratio.
2. Cohort Retention Heatmap (pre-pivoted table, M0–M11) → identify drop-off pattern; dark diagonal = healthy, flat diagonal = systemic churn.
3. Revenue by Cohort — Layer Cake (stacked area by acquisition cohort) → shows whether revenue depends on a few legacy cohorts or is distributed across recent ones.
4. New vs Returning Revenue & Customer Count (6M) → revenue dependency analysis; high new-customer share = fragile growth.

### Tab 3 — Hành vi & Reactivation

**Purpose:** Understand purchase timing and measure win-back effectiveness.

1. Check scalars: Avg Days Between Purchases (campaign timing signal), Reactivated Customers, One-Time Buyer Rate.
2. Purchase Frequency Distribution (histogram) → shape of the one-time vs repeat curve; dominant "1 order" bar = conversion opportunity.
3. Days Between Purchases Distribution → optimal reactivation nudge window; peak bucket = send campaigns just before.
4. Reactivation Trend (combo bar+line) → reactivated count + revenue; rising revenue with flat count = quality improving.

## Key Metrics

| Metric | Definition | Source | Direction |
|:---|:---|:---|:---|
| **Repeat Purchase Rate** | % customers with >1 order as-of month-end snapshot | `mart_customer_status_snapshot_monthly` | Higher ↑ |
| **Churn Rate** | % customers with status = CHURNED at month-end | `mart_customer_status_snapshot_monthly` | Lower ↓ |
| **One-Time Buyer Rate** | % customers with exactly 1 order at month-end | `mart_customer_status_snapshot_monthly` | Lower ↓ |
| **M1 Retention** | % of cohort returning in month after acquisition | `fact_orders` + `dim_customers` | Higher ↑ |
| **Avg Days Between Orders** | Mean inter-purchase gap for repeat customers (gaps > 0 days) | `dim_customers.avg_days_between_orders` | Context-dependent |
| **MAU** | Unique buyers with an order in last 30 days (scope_retail) | `fact_orders` | Higher ↑ |
| **MAU Repeat** | Unique buyers with ≥2 lifetime orders active in the month | `fact_orders` + `dim_customers` | Higher ↑ |

> Full metric definitions → [`../domains/customer.md`](../domains/customer.md) §Retention & Engagement.

## Visualizations

| Chart | Type | Tab | Notes |
|:---|:---|:---|:---|
| Retention Waterfall Trend (6M) | Stacked area | Tab 1 | Uses `mart_retention_waterfall_monthly`; point-in-time, survivorship-free |
| Repeat Purchase Rate Trend (6M) | Line | Tab 1 | Monthly repeat% among buyers that month |
| Retention Health Scorecard | Table | Tab 1 | Per-segment: Active%, At Risk%, Churned%, Repeat Rate%, Avg LTV; conditional color formatting |
| MAU vs Repeat-Buyer MAU (12M) | Dual-line | Tab 1 | Gap = one-time buyer volume |
| Cohort Retention Heatmap | Pivot table (pre-pivoted SQL) | Tab 2 | M0–M11 columns, color-scaled 0–100% |
| Revenue by Cohort — Layer Cake | Stacked area | Tab 2 | 12-month, grouped by acquisition cohort |
| New vs Returning Revenue | Stacked area | Tab 2 | 6-month new/returning split |
| New vs Returning Customers | Stacked bar | Tab 2 | 6-month customer count split |
| Purchase Frequency Distribution | Bar histogram | Tab 3 | Buckets: 1, 2, 3, 4–5, 6–10, 11+ orders |
| Days Between Purchases Dist. | Bar histogram | Tab 3 | Buckets: 0–7, 8–14, 15–30, 31–60, 61–90, 90+ days |
| Reactivation Trend (6M) | Combo (bar + line) | Tab 3 | Bar = count reactivated; line = reactivation revenue |

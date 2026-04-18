---
title: Customer Retention & Lifecycle
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/customer.md]
---

## Design Spec: Customer Retention & Lifecycle

### Brief

- **Audience:** Marketing Manager, Customer Success, CEO — monthly/bi-weekly review
- **Time budget:** 15-20 minutes working session across 3 tabs
- **Primary question:** How well are we retaining customers, and where should we focus to reduce churn and increase repeat purchases?
- **Decision enabled:** Prioritize retention interventions; time reactivation campaigns; identify at-risk high-value customers for outreach
- **Comparison frame:** MoM for KPIs; 6-month trend for patterns; cohort-over-cohort for lifecycle
- **Hero metric:** Repeat Purchase Rate — the most actionable retention signal
- **Archetype:** Operational Cockpit (multi-view, actionable breakdowns)
- **Domain references:** [domains/customer.md](../domains/customer.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude Unknown customers | `customer_id != 'Unknown'` | All cards | System/anonymous records skew metrics |
| Only customers with orders | `total_orders_count > 0` | Most cards | Focus on paying customers |
| Exclude cancelled/voided orders | `status NOT IN ('CANCELLED', 'Voided')` | Order-based cards | Don't count failed transactions |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Customer Segment | category/multi-select | All | Tab 1, Tab 3 cards | Drill into VALUE_VIP/GOLD/SILVER/BRONZE retention |

### Views

Multi-view (3 tabs):
- **View 1 — Suc khoe Retention**: KPI summary + lifecycle status distribution + churn & retention trends
- **View 2 — Phan tich Cohort**: Cohort retention heatmap + revenue layer cake + new vs returning split
- **View 3 — Hanh vi & Reactivation**: Purchase frequency + inter-purchase gaps + win-back tracking + at-risk watchlist

---

### Composition — View 1: Suc khoe Retention

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Monitor retention health — repeat rate, churn, and lifecycle status" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 2 | B | Repeat Purchase Rate | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | % customers with >1 order — core retention signal | vs previous month |
| 3 | B | Churn Rate | supporting | single-value-with-trend | negative/positive (lower=better, MoM) | one-quarter x short, standard | % churned (90+ days inactive) | vs previous month |
| 4 | B | Avg Customer Lifespan | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | Avg days between first and last order (repeat customers) | vs previous month |
| 5 | B | Active Customer Rate | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | % active in last 30 days among all paying customers | vs previous month |
| 6 | C | "Assess lifecycle distribution — where are customers concentrating?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Customer Lifecycle Distribution | breakdown | donut | series-1 (Active), series-2 (At Risk), series-3 (Churned) | one-third x medium | Part-to-whole: what % are in each lifecycle stage | composition |
| 8 | D | Revenue by Lifecycle Status | breakdown | vertical-bar | series-1 (Active), series-2 (At Risk), series-3 (Churned) | one-third x medium | Revenue concentration: how much revenue comes from each status | composition |
| 9 | D | Segment x Status Matrix | breakdown | stacked-bar | series-1 (Active), series-2 (At Risk), series-3 (Churned) | one-third x medium | Which segments have highest churn concentration | composition + rank |
| 10 | E | "Track retention and churn trends — are we improving toward target?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 11 | F | Churn Rate Trend (6M) | trend | line-chart | negative (line), muted (target line) | half x medium | Monthly churn trajectory — is it improving? Target < 40% | vs target + vs previous months |
| 12 | F | Repeat Purchase Rate Trend (6M) | trend | line-chart | positive (line) | half x medium | Monthly repeat rate trajectory — is retention improving? | vs previous months |
| 13 | G | "Review retention scorecard — flag segments with weak retention" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 14 | H | Retention Health Scorecard | detail | data-table-formatted | conditional-above (Repeat% high, Active% >60%), conditional-below (Churn% >40%) | full-width x medium | Per-segment: Customers, Active%, At Risk%, Churned%, Repeat Rate%, Avg LTV, Avg Recency | benchmark (cross-segment) |

### Composition — View 2: Phan tich Cohort

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 15 | A | "Analyze cohort retention — which cohorts stick, which churn early?" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 16 | B | Avg Month-1 Retention | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Average M1 retention across recent cohorts — early lifecycle health | vs previous cohort |
| 17 | B | Best Cohort (M1 Retention) | supporting | single-value | accent | one-quarter x short, standard | Which cohort month had highest M1 retention | — |
| 18 | B | Avg Orders per Customer | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | Purchase frequency indicator | vs previous month |
| 19 | B | New vs Returning Revenue Ratio | supporting | single-value | primary | one-quarter x short, standard | % of revenue from returning customers | — |
| 20 | C | "Examine cohort retention matrix — identify drop-off patterns" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 21 | D | Cohort Retention Heatmap | detail | pivot-table | conditional-range (high retention=positive, low=negative) | full-width x tall | Rows: cohort month, Cols: months since join, Cell: retention % | cohort-over-cohort |
| 22 | E | "Track revenue by cohort — are recent cohorts contributing enough?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | F | Revenue by Cohort (Layer Cake) | trend | stacked-area | series-1..series-N (cohort colors) | full-width x medium | How recent vs legacy cohorts contribute to total revenue | vs previous months |
| 24 | G | "Compare new vs returning — revenue dependency and growth quality" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 25 | H | New vs Returning Revenue (6M) | trend | stacked-area | series-1 (New), series-2 (Returning) | half x medium | Revenue dependency on new vs returning customers | vs previous months |
| 26 | H | New vs Returning Customer Count (6M) | trend | stacked-bar-time | series-1 (New), series-2 (Returning) | half x medium | Volume of new vs returning purchasers each month | vs previous months |

### Composition — View 3: Hanh vi & Reactivation

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 27 | A | "Analyze purchase behavior — timing signals and reactivation effectiveness" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 28 | B | Avg Days Between Purchases | hero | single-value-with-trend | primary, positive/negative (lower=better, MoM) | one-third x short, prominent | Avg inter-purchase gap for repeat customers — timing signal for campaigns | vs previous month |
| 29 | B | Reactivated Customers (Last Month) | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | Customers who returned after 30+ days gap | vs month before |
| 30 | B | At-Risk Customers | supporting | single-value | warning | one-quarter x short, standard | Count of customers 31-90 days since last purchase | — |
| 31 | B | One-Time Buyer Rate | supporting | single-value-with-trend | negative/positive (lower=better, MoM) | one-quarter x short, standard | % with exactly 1 order — conversion opportunity | vs previous month |
| 32 | C | "Examine purchase frequency — distribution shape and conversion opportunity" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 33 | D | Purchase Frequency Distribution | breakdown | vertical-bar | primary (bars) | half x medium | Histogram of order counts — see one-time vs repeat shape | — |
| 34 | D | Days Between Purchases Distribution | breakdown | vertical-bar | secondary (bars) | half x medium | Gap distribution — optimal timing for nudge campaigns | — |
| 35 | E | "Track reactivation performance — is win-back ROI improving?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 36 | F | Reactivation Trend (6M) | trend | combo-chart | positive (Reactivated Customers bar), accent (Revenue from Reactivated line) | full-width x medium | Win-back volume + revenue value — is reactivation working? | vs previous months |
| 37 | G | "Prioritize at-risk outreach — high-value customers needing action NOW" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 38 | H | At-Risk Customer Watchlist | detail | data-table-formatted | conditional-above (LTV high = accent), conditional-below (Recency high = warning) | full-width x medium | Name, Phone, Last Order, Days Since, LTV, Segment — sorted by LTV DESC | rank (by LTV) |
| 39 | I | "Source: dim_customers · fact_orders · Updated monthly · Excludes Unknown & cancelled orders" | annotation | text-annotation | structural | full-width x minimal | Data source & freshness | — |

### Action Map

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| Repeat Purchase Rate (hero) | Decline | MoM < -3pp | Investigate — product quality? pricing? nurture gaps? |
| Churn Rate | Increase | MoM > +5pp | Activate retention campaign, review at-risk watchlist (View 3) |
| Avg Customer Lifespan | Shrinking | MoM < -10% | Review customer experience, post-purchase engagement |
| Churn Rate Trend (6M) | Above target | > 40% for 3 months | Escalate — structural retention problem needs investment |
| Retention Health Scorecard | Segment alert | Any segment Churn% > 50% | Target segment with specific reactivation offer |
| Avg Month-1 Retention (hero V2) | Decline | MoM < -5pp | Investigate onboarding, first-order experience |
| Cohort Retention Heatmap | Early drop-off | M1 < 15% recent cohorts | Review acquisition quality, tighten channel targeting |
| Revenue by Cohort | Legacy dependency | > 70% revenue from cohorts > 6 months old | Increase acquisition investment, improve early cohort monetization |
| Avg Days Between Purchases (hero V3) | Increasing | MoM > +10% | Send purchase reminders earlier, review pricing/promotions |
| At-Risk Customer Watchlist | High-value entries | VIP with > 60 days since last order | Immediate personal outreach — phone call or personalized offer |

### Dashboard Finish Checklist

- [x] Every card has descriptive title
- [x] Every KPI has >=1 comparison
- [x] Text annotations use imperative voice
- [x] No orphan cards
- [x] Action Map complete
- [x] Hero card at top, visually dominant
- [x] Row widths sum = full-width
- [x] Density within Cockpit limits: V1=14, V2=12, V3=12
- [x] Each view has >=1 section divider
- [x] Color tokens consistent
- [x] Size hierarchy clear

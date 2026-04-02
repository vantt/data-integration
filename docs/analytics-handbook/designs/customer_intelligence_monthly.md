---
title: Customer Intelligence Monthly
archetype: Operational Cockpit
status: final
last_modified: 2026-04-02
domain_refs: [domains/customer.md]
---

## Design Spec: Customer Intelligence Monthly

### Brief

- **Audience:** CEO, Marketing Manager, Sales Ops — monthly review meeting, first week of month
- **Time budget:** 15-20 minutes working session across 3 tabs
- **Primary question:** How healthy is our customer base, where is value concentrated, and what behaviors should we act on?
- **Decision enabled:** Prioritize retention vs acquisition investment; target specific segments for campaigns; adjust channel/product strategy by customer type
- **Comparison frame:** MoM (this month vs previous month) for KPIs; 6-month trend for patterns
- **Archetype:** Operational Cockpit (multi-view, actionable breakdowns)
- **Domain references:** [domains/customer.md](../domains/customer.md)

### Constraints & Filters

**Business Constraints:**

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude Unknown customers | `customer_id != 'Unknown'` | All cards | System/anonymous records skew metrics |
| Only customers with orders | `total_orders_count > 0` | Most cards (except acquisition) | Focus on paying customers |
| Exclude cancelled/voided orders | `status NOT IN ('CANCELLED', 'Voided')` | Order-based cards | Don't count failed transactions |

**Interactive Filters:**

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Segment | category/multi-select | All | Tab 2, Tab 3 cards | Drill into specific segment |

### Views

Multi-view (3 tabs):
- **View 1 — Overview & Health**: KPI summary + health scorecard + growth dynamics
- **View 2 — Value & Segmentation**: LTV distribution + segment analysis + AOV trends
- **View 3 — Behavior & Insights**: Channel preference + product affinity + demographics

---

### Composition — View 1: Overview & Health

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Customer Base Health — MoM pulse check on customer growth, activity, and retention" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 2 | B | Total Customers | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Total paying customers, MoM change | vs previous month |
| 3 | B | Active Customers (30d) | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | Customers active in last 30 days | vs previous month |
| 4 | B | New Customers (Last Month) | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | Monthly acquisition volume | vs month before |
| 5 | B | One-Time Buyer Rate | supporting | single-value-with-trend | negative/positive (lower=better, MoM) | one-quarter x short, standard | % customers with only 1 order — conversion opportunity | vs previous month |
| 6 | C | "Customer Status Distribution — Active vs At Risk vs Churned breakdown" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 7 | D | Customer Status Distribution | breakdown | donut | series-1 (Active), series-2 (At Risk), series-3 (Churned) | one-third x medium | Part-to-whole: what % of customers are in each status | composition |
| 8 | D | Customer Segment Distribution | breakdown | donut | series-1 (VIP), series-2 (Loyal), series-3 (Regular) | one-third x medium | Part-to-whole: segment sizes | composition |
| 9 | D | Revenue from Top 20% | supporting | single-value | accent | one-third x medium, prominent | Revenue concentration — Pareto indicator | — |
| 10 | E | "Growth Dynamics — Monthly acquisition vs churn, 6-month trend" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 11 | F | Monthly Acquisition vs Churn (6M) | trend | combo-chart | positive (Acquired bar), negative (Churned bar), primary (Net Growth line) | full-width x medium | Net customer growth trend — bars for volume, line for net | vs previous months |
| 12 | G | "Customer Health Scorecard — Segment-level vitals with conditional alerts" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 13 | H | Customer Health Scorecard | detail | data-table-formatted | conditional-above (Active% >60%), conditional-below (Churned% >30%) | full-width x medium | Per-segment: Active%, At Risk%, Churned%, Repeat%, Avg LTV, Avg Recency | benchmark (cross-segment) |

### Composition — View 2: Value & Segmentation

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 14 | A | "Customer Value Analysis — LTV distribution and segment revenue concentration" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 15 | B | Total Customer LTV | hero | single-value-with-trend | primary, positive/negative (MoM) | one-third x short, prominent | Total lifetime value across all customers | vs previous month |
| 16 | B | Avg LTV per Customer | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | Average customer value | vs previous month |
| 17 | B | Avg Orders per Customer | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | Purchase frequency indicator | vs previous month |
| 18 | B | Repeat Purchase Rate | supporting | single-value-with-trend | positive/negative (MoM) | one-quarter x short, standard | % customers with >1 order | vs previous month |
| 19 | C | "LTV Distribution — Where customers cluster by lifetime value" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 20 | D | Customer Value Distribution | breakdown | vertical-bar | primary (bars), accent (top bucket highlight) | half x medium | Histogram — shape of customer value base | — |
| 21 | D | Segment Revenue Share | breakdown | donut | series-1 (VIP), series-2 (Loyal), series-3 (Regular) | half x medium | Revenue concentration by segment — Pareto visual | composition |
| 22 | E | "Segment Performance Trends — AOV and revenue by segment over 6 months" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 23 | F | AOV by Segment Trend (6M) | trend | multi-line-chart | series-1 (VIP), series-2 (Loyal), series-3 (Regular) | half x medium | AOV trajectory per segment — detect spending changes | vs previous months |
| 24 | F | Revenue by Segment Trend (6M) | trend | stacked-area | series-1 (VIP), series-2 (Loyal), series-3 (Regular) | half x medium | Revenue composition over time — which segments grow | vs previous months |
| 25 | G | "Segment Detail — Comprehensive metrics per segment" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 26 | H | Segment Revenue & Metrics Detail | detail | data-table-formatted | conditional-above (Revenue% high), conditional-below (Recency high) | full-width x medium | Per-segment: Customers, Revenue, Revenue%, Avg Orders, Avg Recency | rank (by revenue) |

### Composition — View 3: Behavior & Insights

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 27 | A | "Purchase Behavior & Channel Intelligence — What customers buy and where" | annotation | text-annotation | structural | full-width x minimal | Dashboard subtitle | — |
| 28 | B | "Channel Effectiveness — Revenue by channel across customer segments (last 3M)" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 29 | C | Channel Revenue by Segment | breakdown | stacked-bar | series-1 (VIP), series-2 (Loyal), series-3 (Regular) | full-width x medium | Which channels drive revenue for each segment | composition |
| 30 | D | "Product Affinity — What VIPs buy vs what first-time buyers buy (last 3M)" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 31 | E | Top 10 Products — VIP Customers | breakdown | horizontal-bar | accent | half x medium | VIP product preferences — guide retention offers | rank |
| 32 | E | Top 10 Products — First-Time Buyers | breakdown | horizontal-bar | primary | half x medium | Entry products — guide acquisition funnels | rank |
| 33 | F | "New Customer Quality — Are we acquiring better or worse customers?" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 34 | G | New Customer Quality Trend (6M) | trend | combo-chart | primary (New Customers bar), accent (Avg First Order line), warning (30-day Repeat % line) | full-width x medium | Cohort quality: volume + first AOV + early repeat rate | vs previous cohorts |
| 35 | H | "Customer Demographics — Gender and loyalty point distribution by segment" | annotation | text-annotation | structural | full-width x minimal | Section heading | — |
| 36 | I | Loyalty Point Distribution | detail | vertical-bar | series-1..series-3 | half x medium | Loyalty engagement level by segment | rank |
| 37 | I | Gender Distribution by Segment | detail | stacked-bar | series-1..series-3 | half x medium | Demographic mix per segment for persona targeting | composition |

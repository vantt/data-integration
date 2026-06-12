# Playbook: Monthly · Customer Intelligence [Cross]

## Overview

- **Audience:** CEO, CMO, Marketing Manager
- **Goal:** Monthly strategic review — customer value, segments, behavior, acquisition.
- **Tool:** metabase
- **Collection:** `Marketing & Customers › 👥 Customer`
- **Cadence:** Monthly (first week of each month)
- **Scope:** `[Cross]` — includes B2B (WHOLESALE, PARTNER); excludes STAFF, KOL, CROSSBORDER
- **Blueprint:** [`../blueprints/metabase/customer_intelligence.md`](../blueprints/metabase/customer_intelligence.md)

## Data Lineage

- **Core Models:** [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql) — RFM `value_group`, `customer_status`, P3 behavioral labels, `lifetime_value`, `recency_days`
- **Fact Tables:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), `fact_sales`, `mart_customer_status_snapshot_monthly`
- **Dimensions:** `dim_channels`, `dim_products`
- **Scope note:** `scope_sales` + `is_active_order` filters apply to all `fact_orders` queries. `mart_customer_status_snapshot_monthly` drives MoM for Total/Active/LTV/Repeat heroes (no YoY until 24 months of data). New Customers hero uses `dim_customers` directly and has YoY.

## Reading Flow

Start here each month — each tab answers one strategic question in sequence:

1. **Tab 1 — Overview & Health:** "How healthy is the customer base this month?" Check KPI row → growth dynamics → segment health scorecard.
2. **Tab 2 — Value & Segmentation:** "Where is revenue concentrated?" Check LTV heroes → LTV distribution → segment revenue trends → segment detail table.
3. **Tab 3 — Behavior & Insights:** "What are customers buying and through which channels?" Check channel effectiveness → product affinity → acquisition quality → demographics/loyalty → discount sensitivity → geo.

> **Seasonal caveat:** For months with major VN retail events (Tết, 11/11, Black Friday), prioritize YoY % over MoM % — MoM comparisons are distorted by seasonality.

## Key Metrics

| Metric | Definition | Source | Alert |
|---|---|---|---|
| Total Customers | Customers with 1+ orders (month-end snapshot) | `mart_customer_status_snapshot_monthly` | — |
| Active Customers (30d) | `status = 'ACTIVE'` at month-end snapshot | `mart_customer_status_snapshot_monthly` | — |
| New Customers | Acquired in prev calendar month; has MoM + YoY | `dim_customers.created_at` | — |
| One-Time Buyer Rate | % with `orders_to_date = 1` at snapshot | `mart_customer_status_snapshot_monthly` | Rising = conversion risk |
| LTV (Total / Avg) | Cumulative revenue per customer | `dim_customers.lifetime_value` | — |
| Avg Orders | Avg `order_count` per customer | `dim_customers` | — |
| Repeat Purchase Rate | % with `orders_to_date > 1` at snapshot | `mart_customer_status_snapshot_monthly` | — |
| Top 20% Revenue Share | Revenue from top quintile / total revenue | `dim_customers` | High = Pareto dependency risk |
| Segment Revenue Share | Revenue split by VALUE_VIP / GOLD / SILVER / BRONZE | `dim_customers` | — |
| Discount Sensitivity | Behavioral: PROMO_DEPENDENT / PROMO_MIXED / FULL_PRICE | `dim_customers.discount_sensitivity` | PROMO_DEPENDENT rising = margin risk |
| Avg Days Between Orders | Mean inter-purchase interval by segment | `dim_customers.avg_days_between_orders` | — |
| Product Affinity | Top 10 products for VIP vs first-time buyers | `fact_sales` + `dim_products` | — |
| Geo by Province | Customers and LTV by province (Top 15) | `dim_customers.province` | — |

> **Discount Sensitivity — behavioral lens only.** This board measures promo dependency (share of discounted orders per customer). The margin cost of those discounts lives in the Profitability board, not here.

## Visualizations

### Tab 1: Overview & Health

| Chart | Viz | Notes |
|---|---|---|
| Total Customers | Scalar + MoM | Snapshot-driven; no YoY yet |
| Active Customers (30d) | Scalar + MoM | `status = 'ACTIVE'` at snapshot |
| New Customers (Last Month) | Scalar + MoM + YoY | From `dim_customers` |
| One-Time Buyer Rate | Scalar + MoM | `orders_to_date = 1`; rising = risk |
| Customer Status Distribution | Donut | Active / At Risk / Churned |
| Customer Segment Distribution | Donut | VIP / GOLD / SILVER / BRONZE |
| Revenue from Top 20% Customers | Scalar | Pareto concentration % |
| Monthly Acquisition vs Churn (6M) | Combo bar+line | Acquired bars, Churned bars, Net Growth line |
| Customer Health Scorecard | Table | Per-segment: Active%, At Risk%, Churned%, Repeat%, Avg LTV, Avg Orders, Avg Recency; conditional formatting |

### Tab 2: Value & Segmentation

| Chart | Viz | Notes |
|---|---|---|
| Total Customer LTV | Scalar + MoM | Snapshot-driven |
| Avg LTV per Customer | Scalar + MoM | Snapshot-driven |
| Avg Orders per Customer | Scalar + MoM | Snapshot-driven |
| Repeat Purchase Rate | Scalar + MoM | Snapshot-driven |
| Customer Value Distribution | Bar histogram | LTV buckets: 0, <500K, 500K-1M, 1M-2M, 2M-5M, 5M-10M, 10M+ |
| Segment Revenue Share | Donut | Revenue by value tier |
| AOV by Segment Trend (6M) | Multi-line | Spending trajectory per segment |
| Revenue by Segment Trend (6M) | Stacked area | Composition shift over time |
| Segment Revenue & Metrics Detail | Table | Customers, Revenue, Revenue%, Avg LTV, Avg Orders, Avg Recency; ranked by revenue |

### Tab 3: Behavior & Insights

| Chart | Viz | Notes |
|---|---|---|
| Channel Revenue by Segment | Stacked bar | Revenue by channel × segment (last 3M) |
| Top 10 Products — VIP Customers | Horizontal bar | Guide retention offers (last 3M) |
| Top 10 Products — First-Time Buyers | Horizontal bar | Guide acquisition funnels (last 3M) |
| New Customer Quality Trend (6M) | Combo | New Customers bar + Avg First Order line + 30d Repeat % line |
| Loyalty Point Distribution by Segment | Stacked bar | 0 / 1-999 / 1K-5K / 5K+ buckets |
| Gender Distribution by Segment | Stacked bar | Demographic mix for persona targeting |
| Discount Sensitivity Distribution | Donut | PROMO_DEPENDENT / PROMO_MIXED / FULL_PRICE share (retail only) |
| Discount Sensitivity by Segment | Normalized stacked bar | Promo dependency cross-tab per value tier |
| Avg Days Between Orders by Segment | Table | Avg, Median, Min, Max days; informs re-engagement timing |
| Top 15 Provinces by Customers | Horizontal bar | Geographic density |
| Top 15 Provinces by LTV | Horizontal bar | Geographic value concentration |
| New Customers by Channel | Horizontal bar | Acquisition channel volume (last month) |
| First-Order Revenue by Channel | Horizontal bar | Acquisition channel value (last month) |

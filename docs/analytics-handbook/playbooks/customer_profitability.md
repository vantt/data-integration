# Playbook: Monthly · Customer Profitability [Retail]

## Overview

- **Audience:** CMO, Finance-Marketing
- **Goal:** Identify which channels and customer segments are contribution-margin positive; gate retail activation decisions on margin health, not just revenue.
- **Tool:** metabase
- **Collection:** `Marketing & Customers › 👥 Customer`
- **Cadence:** Monthly review (90-day rolling window for orders; all-time snapshot for customer attributes)
- **Blueprint:** [`../blueprints/metabase/customer_profitability.md`](../blueprints/metabase/customer_profitability.md)

## Data Lineage

- **`fact_order_economics`** — `channel_net_profit`, `channel_net_margin_pct`; contribution margin after platform fees. Scope: `scope_retail AND has_cogs AND is_active_order` (~65% of orders have COGS coverage).
- **`dim_customers`** — `lifetime_contribution_margin`, `is_margin_negative`, `discount_sensitivity`, `value_group`; all-time snapshot, not date-partitioned.
- **`fact_orders`** — repeat-purchase and discount-amount calculations.
- **`dim_channels`** — channel name lookups.

> **Margin framing:** use `channel_net_margin_pct` (contribution margin) as primary signal. `fully_loaded_margin` allocates overhead by revenue weight — this distorts channel comparison at order grain and penalises large orders. Do **not** use fully-loaded to rank channels.

## Reading Flow

### Tab 1 — Channel × Retention × Margin

**Purpose:** Answer "Which channels are worth growing?"

| Chart | Viz | Notes |
|:---|:---|:---|
| Chu kỳ báo cáo | Scalar | 90-day window label |
| Channel Net Margin % by Channel | Horizontal bar | Contribution margin % per channel; red highlight < 0 |
| Repeat Rate by Channel | Horizontal bar | % customers with >1 order per acquisition channel |
| Channel × Repeat Rate × Contribution Margin | Table | Side-by-side: order share, repeat %, channel net margin %, net profit — the core channel comparison |
| Source & Freshness | Text | Scope notes, has_cogs coverage caveat |

**Reading sequence:** Check which channels sit above zero contribution margin → compare their repeat rates → the Channel Comparison table shows both axes together. Channels with low margin *and* low repeat are migration candidates, not growth targets.

### Tab 2 — Discount-Dependency × Margin

**Purpose:** Answer "Is our discount structure sustainable?"

| Chart | Viz | Notes |
|:---|:---|:---|
| Chu kỳ báo cáo | Scalar | All-time snapshot label |
| Discount Sensitivity Distribution | Pie | PROMO_DEPENDENT / PROMO_MIXED / FULL_PRICE share of retail base |
| Avg Contribution Margin by Discount Sensitivity | Horizontal bar | Margin contrast across sensitivity groups |
| PROMO_DEPENDENT — Discount % of Gross | Scalar | Discount drag as % of gross revenue for PROMO_DEPENDENT |
| Margin-Negative Retail Customers | Scalar | Count of customers with negative lifetime contribution |
| PROMO_DEPENDENT Retail Customers | Scalar | Absolute count of PROMO_DEPENDENT base |
| Discount Sensitivity × Value Tier × Margin Detail | Table | Sensitivity × value_group cross: customer count, margin-negative %, avg contribution, avg LTV |
| Source & Freshness | Text | NULL coverage note (~78% single-purchase customers unclassified) |

**Reading sequence:** Pie shows structural dependency concentration → bar shows how much margin varies across groups → scalars quantify the cost → detail table identifies which tiers are salvageable vs structural write-offs.

## Key Metrics

| Metric | Definition | Threshold / Signal |
|:---|:---|:---|
| Channel Net Margin % | `channel_net_profit / net_revenue` after platform fees | < 0 = channel costs exceed contribution; red alert |
| Repeat Rate by Channel | % customers with >1 order per channel | < 15% = low loyalty; ≥ 30% = healthy retention |
| Contribution Margin by Discount Sensitivity | Avg `lifetime_contribution_margin` per sensitivity group | PROMO_DEPENDENT negative = discount structure unsustainable |
| Margin-Negative Customer Count | Customers where `is_margin_negative = true` | Rising count = discount policy worsening base profitability |
| PROMO_DEPENDENT Discount % of Gross | `SUM(discount_amount) / SUM(gross_revenue)` for PROMO_DEPENDENT | > 40% = discounts consuming most contribution |

## Implementation Notes

- **Scope:** `scope_retail` throughout; excludes `customer_id = 'Unknown'` and cancelled/voided orders.
- **COGS coverage:** `has_cogs` filters to ~65% of orders. Channels with thin coverage may show misleading averages — check order count before acting.
- **Discount sensitivity nulls:** ~78% of retail customers are NULL (single-purchase, insufficient history). Use Tab 2 for structural signal, not individual targeting.
- **PROMO_MIXED caveat:** currently 1 customer — treat as structural placeholder only.
- **Overhead allocation:** fully-loaded margin penalises high-AOV orders due to revenue-weighted overhead split. VIP/GOLD may show negative fully-loaded margin as an artifact — verify allocation key before concluding those tiers are unprofitable.
- **Domain Reference:** [`../domains/customer.md`](../domains/customer.md)

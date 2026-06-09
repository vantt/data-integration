# Plan: Dashboard Quality Improvements

> Created: 2026-06-09
> Status: Backlog
> Origin: `analytics_improvement_opportunities.md` §§ 1–2 (Perspectives + Current Issues)

## Objective

Improve actionability, navigability, and trust of existing dashboards without adding new data sources.
All items here use data already available — this is restructuring and UX work, not data engineering.

---

## Issue 1: Reports stop at diagnosis, not action

Every high-value dashboard should include a sorted action table.

**Standard action table pattern:**

| Field | Purpose |
|---|---|
| Signal | What happened |
| Severity | How urgent |
| Value at Stake | Estimated VND impact |
| Suspected Cause | First likely explanation |
| Owner | Team responsible |
| Suggested Action | What to do next |
| Drill Link | Where to investigate |

**Target dashboards:**
- [ ] Finance P&L — margin leakage queue ranked by VND impact
- [ ] Channel Profitability — channels with highest recoverable margin gap
- [ ] Shopee Channel Economics — fee/voucher/tax breakdown with action flag
- [ ] Sales Promotion Analysis — promo quality matrix (high revenue/low margin → reprice)
- [ ] Customer Retention — ranked outreach list by revenue at risk
- [ ] Orders List Reconciliation — flagged orders with severity score
- [ ] B2B Orders Tracking — collections priority queue
- [ ] Logistics Operations — oldest-stuck queue with customer impact estimate

---

## Issue 2: Profitability is fragmented

Define one drill-down path: Company → Channel → COGS/Discount/Fees → Product/Order → Action.

- [ ] Add cross-links between Finance P&L → Channel Profitability → Order Profitability → Order Detail
- [ ] Add COGS coverage % to top of every margin report
- [ ] Standardise margin taxonomy across all profitability dashboards:
  - Gross Revenue → Net Revenue → COGS → Gross Profit → Platform Fees → Channel Net Profit → (Operating Expenses*) → Net Profit*
  - *mark unavailable until `fact_gl_entries` exists — see `plans/260609-1107-gl-accounting-entries/`

---

## Issue 3: Collection governance inconsistent

`collection_registry.yml` defines: `Executive`, `Marketing & Customers`, `Operations`.
Several dashboards use unregistered paths.

- [ ] Audit all dashboard collection paths vs `collection_registry.yml`
- [ ] Decide: register B2B and CrossBorder as sub-collections, or move into existing three
- [ ] Move Product Analytics under `Executive` or `Operations > Periodic Reviews`
- [ ] Move Customer Support under `Operations`
- [ ] Keep collection paths identical between playbook and blueprint

---

## Issue 4: Playbook / blueprint filename misalignment

**Playbooks without same-name blueprint:**
- [ ] `customer_retention`
- [ ] `finance_cashflow`
- [ ] `logistics_shipping`
- [ ] `order_detail_view`
- [ ] `orders_list_reconciliation`
- [ ] `product_inventory` ← blueprint exists as `product_inventory.md` ✅

**Blueprints without same-name playbook:**
- [ ] `b2b_orders_tracking`
- [ ] `b2b_sales_daily`
- [ ] `customer_retention_dashboard`
- [ ] `marketing_roi`
- [ ] `order_detail`
- [ ] `order_listing`
- [ ] `order_profitability`
- [ ] `order_profitability_all`
- [ ] `product_profitability`
- [ ] `rill/sales_items_product`
- [ ] `us_crossborder_operations`

---

## Issue 5: Scope not visible enough

- [ ] Add scope badge to every dashboard title: `[All]` / `[Retail]` / `[B2B]` / `[US]`
- [ ] Add scope statement to first text card of each dashboard
- [ ] Never mix retail discount/promotion metrics with B2B pricing in the same card

---

## Issue 6: Trust indicators missing from business dashboards

Covered in detail in `plans/260609-1107-data-observability-business-dashboards/`.

- [ ] Add compact trust block (last update, COGS coverage, source warning) to key dashboards
- [ ] For profitability: always show COGS coverage % and Shopee payout lag
- [ ] For daily ops: always show order freshness

---

## Issue 7: Thresholds not calibrated to history

- [ ] Keep fixed policy thresholds (discount > 15%, margin < 25%, etc.)
- [ ] Add historical anomaly flags: above/below 4-week same-day average
- [ ] Add rolling median baseline per channel
- [ ] Use Retail / B2B / US specific thresholds where behavior differs

---

## Domain-specific additions (from Section 1 perspectives)

### Profitability
- [ ] Margin Leakage Queue: rank recoverable leaks by VND (channel × product × order × promo)
- [ ] Add fully-loaded margin path once overhead allocation (`int_order_overhead_allocation`) is stable

### Executive steering
- [ ] Target Gap Bridge in CEO Monthly Scorecard → see `plans/260609-1107-targets-forecasting-pace/`
- [ ] "Top 5 Decisions This Week" table in CEO Weekly Pulse

### Marketing & promotion
- [ ] Contribution ROAS card (revenue − discount − COGS − platform fees − spend)
- [ ] Promo Quality Matrix: high-rev/high-margin → scale; high-rev/low-margin → reprice; low-usage/high-discount → audit
- [ ] Cohort quality by acquisition channel (first AOV, 30/60-day repeat, LTV)

### Customer retention
- [ ] Revenue at Risk card: at-risk customers × trailing LTV, split by VIP/GOLD/SILVER/BRONZE
- [ ] Next Best Action list per segment (VIP at risk → call; churned high-LTV → win-back offer)
- [ ] Campaign Timing Signal: use days-between-purchases distribution to recommend nudge timing

### Product & inventory
- [ ] Product action classification using `mart_inventory_health` × `fact_order_economics`:
  - High velocity, high margin, low stock → reorder
  - High velocity, low margin → reprice
  - Low velocity, high stock → clearance/bundle
- [ ] Product lifecycle state field: new launch / active / seasonal / clearance / discontinued

### Logistics
- [ ] Add SLA by channel/order type to Logistics Operations dashboard
- [ ] Customer impact estimate for stuck orders (customer value, order amount, days delayed)
- [ ] Carrier/delivery SLA tab → see `plans/260609-1107-carrier-shipment-data/`

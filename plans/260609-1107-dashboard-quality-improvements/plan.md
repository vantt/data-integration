# Plan: Dashboard Quality Improvements

> Created: 2026-06-09
> Status: In Progress
> Origin: `analytics_improvement_opportunities.md` §§ 1–2 (Perspectives + Current Issues)
> (updated 2026-06-24: Issues 3-5 largely done; Issues 1/2/7 and domain-specific items still open; 260623 audit fixed Metabase Binder Errors on boards 107-110 commit a925c74 but did not touch action-table or threshold work)
> (re-verified 2026-07-08 against live blueprints/models: Issue 4's `finance_cashflow` blocker was stale — blueprint now exists using `fact_cash_movement`/`fact_account_balance_monthly`, not `fact_payments`; `fact_payments.sql` is also no longer a stub. `customer_daily_action_queue.md` (mart_customer_action_queue) satisfies most of Issue 1's action-table pattern for Customer Retention. `product_health_overview.md` (mart_product_action_queue.action_type: RESTOCK_NOW/CLEAR_DEADSTOCK/REVIEW_MARGIN/PROMOTE/DELIST) satisfies the Product action-classification item. Everything else in Issues 1/2/7 and remaining domain items confirmed still open — see checkbox notes below.)

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
- [ ] Finance P&L — margin leakage queue ranked by VND impact — verified 2026-07-08: no action-table pattern in `finance_pl.md`
- [ ] Channel Profitability — channels with highest recoverable margin gap — verified 2026-07-08: no action-table pattern in `channel_profitability_monthly.md` or `channel_p_l_deep_dive.md`
- [ ] Shopee Channel Economics — fee/voucher/tax breakdown with action flag — verified 2026-07-08: no action-table pattern in `shopee_channel_economics.md`
- [ ] Sales Promotion Analysis — promo quality matrix (high revenue/low margin → reprice) — verified 2026-07-08: only ad-hoc "Signal:...Action:" callout text, no structured table with Severity/Owner/Drill Link
- [x] Customer Retention — `customer_daily_action_queue.md` (mart_customer_action_queue): ranked by `priority_rank`, has `value_at_stake` and `action_type` (CALL_NOW/REORDER_NUDGE/WIN_BACK) as Signal — no explicit Owner/Drill Link columns, close enough to pattern (verified 2026-07-08)
- [ ] Orders List Reconciliation — verified 2026-07-08: `order_listing.md` has no action-table pattern
- [ ] B2B Orders Tracking — verified 2026-07-08: `b2b_orders_tracking.md` has no action-table pattern
- [ ] Logistics Operations — verified 2026-07-08: has a stuck-orders table sorted by wait-hours only (fixed 24h threshold), missing Severity/Value at Stake/Owner columns

---

## Issue 2: Profitability is fragmented

Define one drill-down path: Company → Channel → COGS/Discount/Fees → Product/Order → Action.

- [ ] Add cross-links between Finance P&L → Channel Profitability → Order Profitability → Order Detail — verified 2026-07-08: none found (each blueprint only links within its own tables/design-spec)
- [ ] Add COGS coverage % to top of every margin report — verified 2026-07-08: only `order_profitability_all.md` has it near top; `finance_pl.md`/`channel_profitability_monthly.md` bury it in footnotes; `product_profitability_cost.md` has none
- [ ] Standardise margin taxonomy across all profitability dashboards — verified 2026-07-08: not standardized; `finance_pl.md`/`channel_profitability_monthly.md` use "...→ Channel Net Profit → Fully Loaded Net Profit"; `order_profitability_all.md` stops at "Channel Net Profit"; `product_profitability_cost.md` uses none of these terms:
  - Gross Revenue → Net Revenue → COGS → Gross Profit → Platform Fees → Channel Net Profit → (Operating Expenses*) → Net Profit*
  - *mark unavailable until Net Profit/EBITDA ship — see `plans/260706-1519-balance-sheet-liquidity-ratios/plan.md` Phase 5 (superseded `plans/archive/260609-1107-gl-accounting-entries/`)

---

## Issue 3: Collection governance inconsistent

`collection_registry.yml` defines: `Executive`, `Marketing & Customers`, `Operations`.
Several dashboards use unregistered paths.

- [x] Audit all dashboard collection paths vs `collection_registry.yml`
- [x] Decide: register B2B and CrossBorder as sub-collections, or move into existing three
- [x] Move Product Analytics under `Executive` or `Operations > Periodic Reviews` → resolved as `Analytics`
- [x] Move Customer Support under `Operations` → resolved as `Operations > Daily Monitoring`
- [x] Keep collection paths identical between playbook and blueprint — fixed 10 playbooks 2026-06-10

---

## Issue 4: Playbook / blueprint filename misalignment

**Playbooks without same-name blueprint:**
- [x] `customer_retention` → renamed to `customer_retention_dashboard.md` 2026-06-10
- [x] `finance_cashflow` → blueprint now exists; deployable against `fact_cash_movement`/`fact_account_balance_monthly` (not `fact_payments` as originally assumed — verified 2026-07-08, original blocker was stale; `fact_payments.sql` is also no longer a stub, see `transformation/models/marts/sales/fact_payments.sql`)
- [x] `logistics_shipping` → blueprint created 2026-06-11 using `fact_fulfillments`
- [x] `order_detail_view` → removed 2026-06-11: handled by dedicated detailView app, no dashboard needed
- [x] `orders_list_reconciliation` → renamed to `order_listing.md` 2026-06-10
- [x] `product_inventory` ← blueprint exists as `product_inventory.md`

**Blueprints without same-name playbook:**
- [x] `b2b_orders_tracking` → playbook created 2026-06-10
- [x] `b2b_sales_daily` → playbook created 2026-06-10
- [x] `customer_retention_dashboard` → resolved via rename of `customer_retention.md`
- [x] `marketing_roi` → both already exist
- [x] `order_detail` → no blueprint needed; replaced by detailView app
- [x] `order_listing` → resolved via rename of `orders_list_reconciliation.md`
- [ ] `order_profitability` → blueprint does not exist yet, aspirational
- [x] `order_profitability_all` → playbook created 2026-06-10
- [x] `product_profitability` → playbook created 2026-06-10
- [ ] `rill/sales_items_product` → YAML format, out of scope for MD playbooks

**Clarification (2026-06-11):** `sales_today_operation` and `sales_daily_operation` are TWO intentional separate dashboards — `today` shows live today-only report; `daily` shows report by selectable date filter. Not a mismatch.

**Blueprints without playbook (discovered 2026-06-11, not yet tracked):**
- [x] `customer_action_queue.md` → playbook created 2026-06-11
- [x] `order_revenue_explorer.md` → playbook created 2026-06-11
- [x] `welcome_landing.md` → onboarding landing page, no playbook needed
- [x] `us_crossborder_operations` → playbook created 2026-06-10

---

## Issue 5: Scope not visible enough

- [x] Add scope badge to every dashboard title: `[All]` / `[Retail]` / `[B2B]` / `[US]` — all blueprints verified 2026-06-10
- [x] Add scope statement to first text card of each dashboard — done per blueprint text cards
- [x] Never mix retail discount/promotion metrics with B2B pricing in the same card — enforced by design

---

## Issue 6: Trust indicators missing from business dashboards

→ Moved to `plans/260609-1107-data-observability-business-dashboards/`

---

## Issue 7: Thresholds not calibrated to history

- [x] Keep fixed policy thresholds (discount > 15%, margin < 25%, etc.) — already in place across blueprints
- [ ] Add historical anomaly flags: above/below 4-week same-day average — verified 2026-07-08: no "4-week"/anomaly-flag logic found anywhere in blueprints/models
- [ ] Add rolling median baseline per channel — verified 2026-07-08: no rolling-median logic found; only 2 files have any historical baseline at all — `sales_promotion_analysis.md` (rolling-30d non-promo same-channel baseline AOV) and `marketing_monthly_analysis.md` (CTE `baseline`) — neither is channel-median-based, and neither covers the target dashboards (`logistics_operations.md` stuck-orders table still uses a fixed 24h threshold)
- [ ] Use Retail / B2B / US specific thresholds where behavior differs — not verified as implemented

---

## Domain-specific additions (from Section 1 perspectives)

### Profitability
- [ ] Margin Leakage Queue: rank recoverable leaks by VND (channel × product × order × promo) — verified 2026-07-08: not found anywhere in docs/
- [x] Add fully-loaded margin path once overhead allocation (`int_order_overhead_allocation`) is stable — verified 2026-07-08: model exists at `transformation/models/intermediate/overhead/int_order_overhead_allocation.sql`, has actual/estimated branches, feeds `fact_order_costs.sql`/`fact_order_economics.sql`, and "Fully Loaded Net Profit" already appears in `finance_pl.md`/`channel_profitability_monthly.md`

### Executive steering

→ Moved to `plans/260609-1107-targets-forecasting-pace/`

### Marketing & promotion
- [ ] Contribution ROAS card (revenue − discount − COGS − platform fees − spend) — verified 2026-07-08: not found in `marketing_roi.md`/`sales_promotion_analysis.md`/`marketing_monthly_analysis.md`
- [ ] Promo Quality Matrix: high-rev/high-margin → scale; high-rev/low-margin → reprice; low-usage/high-discount → audit — verified 2026-07-08: not found
- [ ] Cohort quality by acquisition channel (first AOV, 30/60-day repeat, LTV) — verified 2026-07-08: not found

### Customer retention
- [ ] Revenue at Risk card: at-risk customers × trailing LTV, split by VIP/GOLD/SILVER/BRONZE — verified 2026-07-08: `customer_daily_action_queue.md` has `value_at_stake` but not confirmed split by VIP/GOLD/SILVER/BRONZE
- [ ] Next Best Action list per segment (VIP at risk → call; churned high-LTV → win-back offer) — verified 2026-07-08: partially covered by `mart_customer_action_queue.action_type` (CALL_NOW/REORDER_NUDGE/WIN_BACK) in `customer_daily_action_queue.md`, but not confirmed segment-specific (VIP/GOLD/SILVER/BRONZE)
- [ ] Campaign Timing Signal: use days-between-purchases distribution to recommend nudge timing — verified 2026-07-08: not found

### Product & inventory
- [x] Product action classification using `mart_inventory_health` × `fact_order_economics` — verified 2026-07-08: implemented as `mart_product_action_queue.action_type` in `product_health_overview.md` with RESTOCK_NOW / CLEAR_DEADSTOCK / REVIEW_MARGIN / PROMOTE / DELIST (maps to reorder/clearance/reprice intent, though label names differ from original wording)
- [ ] Product lifecycle state field: new launch / active / seasonal / clearance / discontinued — not verified as implemented (exact field with these 5 states not confirmed)

### Logistics
- [ ] Add SLA by channel/order type to Logistics Operations dashboard — verified 2026-07-08: "SLA" not found literally in `logistics_operations.md` or `logistics_shipping.md`
- [ ] Customer impact estimate for stuck orders (customer value, order amount, days delayed) — verified 2026-07-08: `logistics_operations.md` stuck-orders table only has wait-hours (fixed 24h threshold), no customer-value/order-amount columns
- ~~Carrier/delivery SLA tab~~ → Moved to `plans/260609-1107-carrier-shipment-data/`

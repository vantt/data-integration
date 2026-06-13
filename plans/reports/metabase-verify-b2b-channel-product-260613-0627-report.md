# Metabase Dashboard Purpose Verification
**Date:** 2026-06-13 | **Scope:** 9 dashboards vs. intended plan purpose

---

## B2B Dashboards

### D49 — B2B Daily Sales
**Verdict: MATCH**
- All KPI cards (Net Revenue, Orders, AOV, Unique Customers) filter `WHERE o.scope_b2b` — confirmed via card 1364 SQL.
- Revenue breakdown cards ("Revenue by Customer Type", "Revenue by Channel (B2B)") scoped to B2B segment.
- Top Customers and Orders List cards also on `scope_b2b`.

### D50 — B2B Orders Tracking
**Verdict: MATCH**
- Outstanding/payment cards filter `WHERE o.scope_b2b AND o.payment_status IN ('UNPAID','PARTIAL')` — confirmed card 1372.
- Fulfillment tab (Pending, In Transit, Delivered) correctly scoped to B2B wholesale.

---

## Channel Economics Dashboards

### D33 — Channel Profitability Monthly
**Verdict: MATCH**
- Covers all channels via `int_misa_sales_lines` grouped by `channel_name`. Margin %, Revenue vs COGS, Trend by Channel, Top/Bottom products all present.
- **Core vs marketplace split: NOT present.** Cards group raw `channel_name` only — no `channel_type` / `channel_group` / `is_marketplace` segmentation found in SQL (cards 1105, 1106, 1107 checked).

### D77 — Channel P&L Deep Dive
**Verdict: MATCH** (with caveat)
- Strong P&L analysis: Waterfall (1504), Scorecard Table (1505), Margin Heatmap (1506), MoM Variance, Loss Leader analysis.
- D77 description: "Channel nào lỗ sau khi trừ phí platform?" — correctly answered by the cards.
- **Core vs marketplace split: NOT present.** Checked 1504, 1505, 1506, 1509, 1988 — all group by raw channel, no explicit core/marketplace grouping column or filter.

### D32 — Shopee Channel Economics
**Verdict: MATCH**
- Fully scoped to `int_shopee_order_fees` — Shopee-only source table (confirmed card 1091).
- Settlement margin, fee breakdown, waterfall, scatter, below-breakeven cards all present and Shopee-specific.
- Functions correctly as the "marketplace" deep-dive; complements D33/D77 which cover all channels.

---

## Explicit Answer (a): Do channel dashboards split core vs marketplace?

**NO.** D33 and D77 group by raw `channel_name` with no `channel_type`, `channel_group`, or `is_marketplace` column in SQL. The plan's intended "core channels (B2B+Social+Web) vs marketplace (Shopee+CrossBorder)" separation **is not implemented** in these dashboards. D32 provides Shopee-only depth but the cross-dashboard grouping is absent.

---

## Product Analytics Dashboards

### D107 — Product Health Overview
**Verdict: MATCH**
- STAR / WORKHORSE / QUESTION / DOG health classification present (cards 2312–2316, 2319).
- ABC class + lifecycle stage distribution cards present.
- Tab 2: Action queue (RESTOCK_NOW, CLEAR_DEADSTOCK, REVIEW_MARGIN, PROMOTE, DELIST) with count + value cards — matches plan intent.

### D109 — Product Performance & Velocity
**Verdict: MATCH**
- Revenue, qty, velocity KPIs by day, by product type present.
- Top 20 by revenue/qty/velocity, MoM gainers/losers (2356, 2357) present.
- ACCELERATING/DECELERATING momentum cards (2360, 2361) + health classification table — matches plan description exactly.

### D108 — Product Profitability & Cost
**Verdict: MATCH**
- Tab 1: SKU margin ranking (top profit 2335, bottom margin 2336, channel margin 2337, detail table 2338).
- Tab 2: COGS variance alerts (2341 count, 2345 alert table), margin distribution histogram (2344), scatter plot (2342).
- Matches plan: "SKU margin ranking + COGS variance anomalies."

### D110 — Product Inventory & Stock Health
**Verdict: MATCH**
- OOS SKUs card (2363): `WHERE is_oos = true` from `mart_inventory_health` — confirmed via SQL.
- OOS Risk SKUs (2367): `WHERE oos_risk = true` from `mart_product_health` (high-velocity + low stock detection).
- Danh Sách SKU OOS (2370): full OOS SKU detail list with on_hand, committed, incoming, days_of_supply.
- Slow-mover and dead-stock exposure cards (2371–2377), 90-day trend cards present.

---

## Explicit Answer (b): Does D110 cover OOS / low-stock hero-SKU detection?

**YES.** D110 has dedicated `is_oos` and `oos_risk` KPI cards from `mart_inventory_health` / `mart_product_health`, a full OOS SKU detail list, and OOS Rate trend over 90 days. Hero-SKU (high-velocity + low stock) detection confirmed via card 2367 `oos_risk = true`.

---

## Summary Table

| Dashboard | Verdict | Key Gap |
|-----------|---------|---------|
| 49 B2B Daily Sales | MATCH | — |
| 50 B2B Orders Tracking | MATCH | — |
| 33 Channel Profitability Monthly | MATCH | No core/marketplace split |
| 77 Channel P&L Deep Dive | MATCH | No core/marketplace split |
| 32 Shopee Channel Economics | MATCH | — |
| 107 Product Health Overview | MATCH | — |
| 109 Product Performance & Velocity | MATCH | — |
| 108 Product Profitability & Cost | MATCH | — |
| 110 Product Inventory & Stock Health | MATCH | — |

---

## Unresolved Questions

1. **Core vs marketplace split gap** — Plan requires "core channels (B2B+Social+Web) vs marketplace (Shopee+CrossBorder)" grouping in D33/D77. Is `channel_type` / `is_marketplace` column present in `dim_channels`? If yes, dashboards need a grouping card; if not, the mart layer needs the column first.
2. **D49/D50 unnamed cards** — Several dashcards returned `CID=? | ?` (text/separator cards with no card object). Not a functional concern but worth confirming none are broken queries.
3. **`fact_payments` empty** — D50 tracks payment status via soft flags on `fact_orders`; actual cash verification unavailable. Known limitation per project memory.

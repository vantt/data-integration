# Semantic Contract Population Report

**Date:** 2026-06-06
**Task:** Exhaustive scan + population of docs/analytics-handbook/semantic/ (6 files)
**Sources scanned:** 10 domain/guide docs (Tier 1) + 3 Rill YAML + 2 mart SQL (Tier 2) + blueprint list review (Tier 3 spot-check)

---

## Concepts Found & Added

| Category | Existing (before) | Added | Total |
|---|---|---|---|
| Segments | 3 (scope_sales, scope_retail, scope_b2b) | 4 (filter_us, filter_internal, filter_social, filter_has_cogs) | 7 |
| Metrics | 8 (revenue waterfall + AOV + VAT) | ~45 (Finance×12, Logistics×4, Customer×7, Product×4, Marketing×7, Health×1, Ops×3) | ~53 |
| Dimensions | 18 (channel×5, customer×3, time×3, location×3, status×4) | ~22 (staff×4, product×5, channel_extra×3, fulfillment×5, discount×3, customer_behavioral×4, marketing×3) | ~40 |
| Entities | 6 (Order, OrderLineItem, Customer, Channel, Product, OrderEconomics) | 10 (Returns, OrderCosts, MarketingSpend, InventorySnapshot, InventoryHealth, SKUEconomics, Fulfillment, Staff, ChannelTargets, Targets, Payments) | ~16 |
| Rules | 5 (VAT, Cancellation, is_completed, OrderCount, ScopePromotion, DateKeyTZ) | 8 (COGSSourcing, OverheadAlloc, PromoGoodsCost, ShopeeServiceFee, MISAChannel, isPromoLine, ReturnsP&L, DiscountClassification, KY_GUI_Partner) | ~14 |
| Freshness SLA | 7 marts | +11 marts/seeds | 18 |

---

## Conflicts / Ambiguities Requiring Human Review

1. **✅ RESOLVED: gross_profit definition cross-domain**
   - Canonical: `fact_order_economics.gross_profit` (pre-computed column). Documented in `semantic/metrics.md`.
   - MISA line-level `int_misa_sales_lines.gross_profit` is a source table intermediate — not for dashboard use.

2. **✅ RESOLVED: return_rate definition — 3 different expressions found**
   - Split into 3 named metrics in `semantic/metrics.md`:
     - `return_rate` → `fact_order_returns` / `scope_sales` orders (Finance/P&L canonical)
     - `post_ship_return_rate` → shipped denominator + 30-day post-ship window (Logistics SLA)
     - `return_count` → raw count for daily ops
   - `fulfillment_status='RETURNED'` approach deprecated — undercounts partial returns.

3. **✅ RESOLVED: AOV formula — net_revenue vs total_collected**
   - Canonical: `SUM(net_revenue) / NULLIF(COUNT(DISTINCT order_id), 0) WHERE scope_retail`
   - `dim_customers.avg_order_value` uses `total_collected` for customer scoring only — documented as intentional difference in `semantic/metrics.md`.

4. **⚠️ OPEN: customer_type=CROSSBORDER in production**
   - Documented in `semantic/dimensions.md`: appears in `dim_customers` but excluded at channel level (`is_sales_channel=false`).
   - Not yet verified via SQL whether rows actually exist in production `dim_customers`.

5. **✅ NOTED: customer_type migration incomplete**
   - Documented in `semantic/dimensions.md` and memory. Historical B2B (scope_b2b) before 2026 unreliable. Not a blocking ambiguity.

---

## Blueprints Re-deriving Instead of Using Semantic Columns

✅ **DONE (2026-06-06):**
- All 38 blueprints now have YAML frontmatter (`primary_scope`, `scope_indicator`, `layer`, `uses_concepts`) and `## Segmentation Scope` section.
- `semantic/README.md` updated with Blueprint Integration Standard.
- `create_blueprint.js` scaffold includes frontmatter + scope section template.
- `validate-analytics-artifacts.js` enforces frontmatter presence and warns on SQL anti-patterns.

⚠️ **BACKLOG:** 32 SQL warnings remain — blueprints still use inline scope derivation in SQL (e.g. `customer_type='RETAIL'` instead of `WHERE scope_retail`). Dashboards functional; SQL migration is cleanup only.

---

## Missing / Not Yet Captured

- `fact_gl_entries` — General Ledger planned mart (not yet built). Operating Margin, Net Margin, EBITDA, DSO are planned metrics with no implementation yet. Documented as "Planned" in finance.md.
- `fact_shipments` — Planned mart replacing std_fulfillments. Carrier Performance and Shipment Operations metrics currently `planned`.
- `dim_carriers` — Not yet seeded. Carrier-level analysis blocked.
- Facebook Ads / Messenger marts (`fact_fb_ads_insights_daily`, `dim_fb_conversations`) — discovered in transformation glob but not documented in any domain docs. No freshness SLA captured.
- `mart_customer_status_snapshot_monthly` — discovered in transformation but not in domain docs. Unknown freshness SLA.

---

## Unresolved Questions

1. **⚠️ OPEN:** Does `customer_type = 'CROSSBORDER'` actually appear in production `dim_customers`? Need SQL verification.
2. **✅ RESOLVED:** `return_rate` for health score = `return_rate` (refunds via `fact_order_returns`). `repeat_buyer_rate` is the loyalty/retention metric — named differently, not confused.
3. **⚠️ OPEN:** `fact_fb_ads_insights_daily` and `dim_fb_conversations` — active or deprecated? No domain docs coverage.
4. **⚠️ OPEN:** `mart_customer_status_snapshot_monthly` — purpose and freshness SLA unknown.
5. **⚠️ OPEN:** Overhead allocation formula — revenue-proportional or order-count-proportional? Design docs in `docs/architecture/order-pl/` not yet surfaced in semantic layer.

**Status:** DONE_WITH_CONCERNS
**Summary:** Populated all 6 semantic files with ~100+ new concept entries. 5 ambiguities flagged for human resolution, particularly the 3 conflicting return_rate definitions and AOV formula discrepancy between Rill and dim_customers.
**Concerns:** return_rate has 3 incompatible implementations; customer_type=CROSSBORDER existence unverified; Facebook Ads + messenger marts undocumented.

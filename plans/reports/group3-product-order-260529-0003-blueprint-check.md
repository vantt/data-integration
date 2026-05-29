# Group 3 Blueprint Check — Product + Order + Logistics
**Date:** 2026-05-29 | **Run:** #2 (post-fix)

## Summary Table

| ID | Dashboard | BP Q | MB Q | Missing | Extra | Text (BP/MB) | Status |
|---|---|---|---|---|---|---|---|
| 35 | Order Profitability [All] | 10 | 10 | — | — | 6/6 | **MATCH** |
| 38 | Order Detail [Retail] | 5 | 5 | — | — | 5/5 | **MATCH** |
| 26 | Order Listing [Retail] | 14 | 14 | — | — | 22/22 | **MATCH** |
| 30 | Product Performance [Cross] | 23 | 23 | — | — | 18/18 | **MATCH** |
| 36 | Product Profitability [All] | 8 | 8 | — | — | 4/4 | **MATCH** |
| 94 | Product Inventory Health [All] | 20 | 20 | — | — | 3/3 | **MATCH** |
| 28 | Logistics Operations Center [All] | 19 | 19 | — | — | 12/12 | **MATCH** |

## Detail per Dashboard

### ID 35 — Order Profitability [All]
- Blueprint: `docs/analytics-handbook/blueprints/order_profitability_all.md`
- Tabs: none (both)
- Questions: 10/10 exact match
- Text cards: 6/6 (Cycle Indicator, Section P&L, Section Channel, Section Detail, Section Order List, Source & Freshness)
- **MATCH**

### ID 38 — Order Detail [Retail]
- Blueprint: `docs/analytics-handbook/blueprints/order_detail.md`
- Tabs: none (both)
- Questions: 5/5 — Chu ky bao cao, Order Header, Order Economics, Line Items, Payments
- Text cards: 5/5
- **MATCH** — Note: dashboard was redeployed with [Retail] suffix after last run

### ID 26 — Order Listing [Retail]
- Blueprint: `docs/analytics-handbook/blueprints/order_listing.md`
- Tabs: Today / Yesterday / By Date — both match
- Questions: 14/14 unique (deduplicated across 3 tabs)
- Text cards: 22/22
- **MATCH**

### ID 30 — Product Performance [Cross]
- Blueprint: `docs/analytics-handbook/blueprints/product_performance.md`
- Tabs: Tong quan / Phan tich loai san pham / San pham ban chay & ban cham / Loi nhuan — both match
- Questions: 23/23 exact match
- Text cards: 18/18
- **MATCH**

### ID 36 — Product Profitability [All]
- Blueprint: `docs/analytics-handbook/blueprints/product_profitability.md`
- Tabs: none (both)
- Questions: 8/8 — Chu ky bao cao, Total Products, Avg Margin %, Highest/Lowest Margin Product, Top Products by Profit, Bottom Margin Products, Product Detail Table
- Text cards: 4/4
- **MATCH**

### ID 94 — Product Inventory Health [All]
- Blueprint: `docs/analytics-handbook/blueprints/product_inventory.md`
- Tabs: Current Stock / Slow-Mover & Dead Stock / Inventory Trend — both match
- Questions: 20/20 (Chu ky bao cao deduplicated from 3 per tab to 1 in MB — expected behavior)
- Text cards: 3/3
- **MATCH**

### ID 28 — Logistics Operations Center [All]
- Blueprint: `docs/analytics-handbook/blueprints/logistics_operations.md`
- Tabs: Tong quan / Toc do xu ly / Chi tiet & Nhan vien — both match
- Questions: 19/19 (Chu ky bao cao deduplicated from 3 tabs to 1 — expected)
- Text cards: 12/12
- **MATCH**

## Verdict

**All 7 dashboards: MATCH.** Group 3 is fully aligned post-fix. Zero drift detected.

## Notes

- MB deduplicates questions shared across tabs (same card reused) — "Chu ky bao cao" appears once in MB even if multiple tabs have it; blueprint counts likewise normalized.
- Text card count for ID 35 initially appeared diff=1 due to miscounting blueprint — actual count is 6/6.
- Methodology: compared `dashcards[]` where `card_id != null` (questions) vs `card_id == null` (text cards); tab names from `tabs[]`.

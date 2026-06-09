# Pattern A Investigation — source-freshness at row=0

**Date:** 2026-05-29  
**Scope:** 4 dashboards, 4 tabs with source card at row=0

---

## Root Cause

**Structural defect in blueprint markdown.** When a `#### 📝 Text: <Heading>` section has no body content between it and the next `#### 📝 Text: Source & Freshness` section, the deploy script merges the source content + the following heading body into a **single dashcard**. That merged card picks up the heading's `metabase-pos` (row=0) rather than the source's pos (row=99).

Pattern in all affected tabs:
```
#### 📝 Text: <Heading>
(empty — no content here)

#### 📝 Text: Source & Freshness
**Source:** ...
<!-- text-id:source-freshness -->
```json metabase-pos
{ "row": 99 }
```

## <Heading content>
```json metabase-pos
{ "row": 0 }    ← this row=0 gets assigned to the merged source+heading card
```
```

---

## Per-Tab Findings

### D44 — Tab: Sản phẩm & Vận hành

| Attribute | Value |
|---|---|
| Live card at row=0 | id=1810, merged source+heading text, col=0 size=18x1 |
| Cycle-indicator at row=0 | id=2852 (correct, expected) |
| Conflict? | YES — 3 cards at row=0: heading, source (id=1810), cycle-indicator |
| Duplicate source? | YES — old-format source at row=23 (id=2983) also exists |
| Max-row card | id=2983 row=23 old-format "Source: fact_orders..." |

**Root cause:** Blueprint had source section between empty heading section and heading body content. Merged card deployed to row=0.

**Fix:** Moved heading body (`## Xác định sản phẩm...` + `metabase-pos row=0`) to be directly under `#### 📝 Text: Xác định...`, before the Source section.

**Blueprint:** `docs/analytics-handbook/blueprints/ceo_monthly_scorecard.md`  
**Lines changed:** Tab "San pham & Van hanh" — reordered sections ~L1313-L1329

---

### D46 — Tab: Discount ROI

| Attribute | Value |
|---|---|
| Live card at row=0 | id=2962, merged source+heading text, col=0 size=18x1 |
| Cycle-indicator at row=0 | id=2961 (correct, expected) |
| Conflict? | YES — 3 cards at row=0: heading text, source (id=2962), cycle-indicator |
| Duplicate source? | YES — old-format "Footer" source at row=27 (id=2380) also exists |
| Max-row card | id=2380 row=27 old-format "Source: fact_orders · dim_promotions..." |

**Root cause:** Same structural defect — `#### 📝 Text: Discount ROI` had no body content, source section followed immediately, heading body at row=0 came after.

**Fix:** Moved heading body (`## Discount ROI...` + `metabase-pos row=0`) to be directly under `#### 📝 Text: Discount ROI...`, before the Source section.

**Blueprint:** `docs/analytics-handbook/blueprints/sales_promotion_analysis.md`  
**Lines changed:** Tab "Discount ROI" section ~L1480-L1496

---

### D32 — Tab: Shopee P&L Cascade

| Attribute | Value |
|---|---|
| Live card at row=0 | id=2887, merged source+heading text, col=0 size=18x1 |
| Cycle-indicator at row=0 | id=2886 (correct, expected) |
| Conflict? | YES — 3 cards at row=0: PnL heading, source (id=2887), cycle-indicator |
| Duplicate source? | NO — source id=2887 is the ONLY source in this tab |
| Max-row card | id=2383 row=10 chart "Orders Below Breakeven" |

**Root cause:** Same structural defect — `#### 📝 Text: PnL Cascade Heading` had no body, source followed immediately, heading body had row=0. Since max_row=10 is a chart (not a source), the source needs to go to row=11 (after the chart).

**Fix:** 
1. Moved heading body (`## Shopee P&L Cascade...` + `metabase-pos row=0`) under the heading section.
2. Changed source `metabase-pos` from row=99 → row=11 (directly after the last chart at row=2..10).

**Blueprint:** `docs/analytics-handbook/blueprints/shopee_channel_economics.md`  
**Lines changed:** Tab "Shopee P&L Cascade" section ~L657-L673

---

### D26 — Tab: By Date

| Attribute | Value |
|---|---|
| Live card at row=0 | id=2894, merged source+reconciliation-checklist text, col=0 size=15x2 |
| Cycle-indicator at row=0 | id=2893 (correct, expected) |
| Conflict? | YES — 4 cards at row=0: Data Freshness, Recon Checklist, source (id=2894), cycle-indicator |
| Duplicate source? | YES — another new-format source at row=99 (id=3237) + old-format at row=36 (id=1526) |
| Max-row card | id=3237 row=99 new-format source (correct position) |

**Root cause:** Same structural defect — `#### 📝 Text: Reconciliation Checklist` had no body, source section followed, checklist body content with row=0 came after.

**Fix:** Moved checklist body content + `metabase-pos row=0` to be directly under `#### 📝 Text: Reconciliation Checklist`, before the Source section. Source remains at row=99.

**Blueprint:** `docs/analytics-handbook/blueprints/order_listing.md`  
**Lines changed:** Tab "By Date" section ~L1250-L1272

---

## Summary Table

| Dashboard | Tab | Live Source Row | Duplicate? | Fix Applied |
|---|---|---|---|---|
| D44 CEO Monthly Scorecard | Sản phẩm & Vận hành | 0 (id=1810) | YES (row=23 old) | Reordered heading+source in blueprint |
| D46 Promotion Analysis | Discount ROI | 0 (id=2962) | YES (row=27 old) | Reordered heading+source in blueprint |
| D32 Shopee Channel Economics | Shopee P&L Cascade | 0 (id=2887) | NO (only source) | Reordered + changed source row to 11 |
| D26 Order Listing | By Date | 0 (id=2894) | YES (row=99 new) | Reordered checklist+source in blueprint |

## Files Modified

- `docs/analytics-handbook/blueprints/ceo_monthly_scorecard.md`
- `docs/analytics-handbook/blueprints/sales_promotion_analysis.md`
- `docs/analytics-handbook/blueprints/shopee_channel_economics.md`
- `docs/analytics-handbook/blueprints/order_listing.md`

## Next Steps

- Redeploy affected tabs to Metabase to fix live dashboard layout
- For D44 tab Sản phẩm, D46 tab Discount ROI, D26 tab By Date: also delete the duplicate source card at row=0 in Metabase (ids: 1810, 2962, 2894) — these are orphan cards not from blueprint
- For D32 tab Shopee P&L: the source card id=2887 currently at row=0 will move to row=11 on redeploy

## Unresolved Questions

- D44 Tab Sản phẩm: old-format source at row=23 (id=2983, text-id:source-freshness-2) — should this be removed? Blueprint has `Source: fact_orders · Updated monthly...` at row=23 which is different from the new-format source at row=99. Recommend removing old-format on redeploy.
- D46 Tab Discount ROI: old-format "Footer" at row=27 (id=2380) still in blueprint as `#### 📝 Text: Footer`. Recommend removing on redeploy.
- D46 Tab Phan tich kenh & chi tiet: also has old-format source at row=24 (id=1856) — not in scope of Pattern A but same cleanup needed.

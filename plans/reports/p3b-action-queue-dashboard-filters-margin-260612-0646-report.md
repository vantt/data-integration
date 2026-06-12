# P3B Action Queue Dashboard — Filters + Margin + REORDER_PREEMPT

**Date:** 2026-06-12 | **Dashboard:** #99 Customer Action Queue [Retail] | **Blueprint:** `docs/analytics-handbook/blueprints/customer_action_queue.md`

---

## Pre-Deploy Safety Check

- Live dashboard 99 matched blueprint exactly (13 cards, 2 filters: action_type, value_group).
- Card 2175 SQL verified via `/api/card/2175` → `dataset_query.stages[0].native` matched blueprint verbatim. No divergence.
- New mart columns (`is_contactable`, `lifetime_contribution_margin`, `is_margin_negative`) confirmed present in latest parquet (`mart_customer_action_queue_20260611235115.parquet`) but NOT yet synced to Metabase table 138.
- Triggered `/api/table/138/rescan_values` + `/api/database/2/sync_schema` → new field_ids resolved: 1661 (`is_contactable`), 1662 (`lifetime_contribution_margin`), 1663 (`is_margin_negative`).
- `REORDER_PREEMPT` confirmed live in parquet (3 rows).

---

## Blueprint Changes (customer_action_queue.md)

**Filters added (2):**
- `is_contactable` — `string/=`, field_id 1661, default `"true"` (shows only reachable customers by default)
- `next_purchase_signal` — `string/=`, field_id 760

**New scalar card:**
- `REORDER_PREEMPT — Nhac truoc` (card 2225) at row 3, col 9, size_x 3 — "DUE_SOON — sắp đến hạn tái mua"
- Scalar row reshuffled from 4/4/4/3/3 → 3/3/3/3/3/3 to fit 6 cards in 18 cols.

**Queue table card (2175) — SQL changes:**
- Added `REORDER_PREEMPT → '⏰ Nhắc trước'` to action_type CASE
- Added columns: `is_contactable AS "Liên lạc được"`, `lifetime_contribution_margin AS "Biên đóng góp"`, `is_margin_negative AS "Âm biên"`
- Added filter wiring: `[[AND {{is_contactable}}]]`, `[[AND {{next_purchase_signal}}]]`
- `Biên đóng góp` default-off in table.columns (column still queryable, CS can enable)
- `Âm biên` column formatting: red highlight when true

**Breakdown charts (2173, 2174):**
- Added `REORDER_PREEMPT → '3. Nhắc trước ⏰'`; existing entries renumbered 3→4→5→6.

---

## Deploy Output (tail)

```
✅ Created Question 'REORDER_PREEMPT — Nhac truoc' (ID: 2225)
✅ Updated Question 'Queue — Danh sach outreach' (ID: 2175)
✅ Synced cards. Dashboard now has 14 cards.
🚀 Deployment Complete.
```

Warnings about `action_type`/`is_contactable`/`next_purchase_signal` not matched to scalar cards are **expected** — scalar cards hardcode their own `WHERE action_type = '...'` and are not intended to receive contactable/signal filters.

---

## Post-Deploy Verification

| Check | Result |
|---|---|
| Filters on dashboard 99 | 4: action_type, value_group, is_contactable (default=true), next_purchase_signal ✅ |
| REORDER_PREEMPT scalar (card 2225) | Present at row 3, col 9 ✅ |
| Queue table columns | 16 cols incl. Liên lạc được, Biên đóng góp, Âm biên ✅ |
| Query row count | 116 rows returned ✅ |
| is_contactable default filter | true (live) ✅ |

---

**Status:** DONE
**Summary:** Added 2 new dashboard filters (is_contactable default=true, next_purchase_signal), new REORDER_PREEMPT scalar card, margin columns (Biên đóng góp default-off, Âm biên with red flag) to queue table. All deployed via blueprint workflow; 14 cards live, all verified.
**Concerns:** `next_purchase_signal` field_id 760 was on table 138 pre-existing but had no `semantic_type` — Metabase may show it as text input rather than dropdown until field values are indexed. Rescan was triggered; if dropdown doesn't appear, run `/api/field/760/rescan_values` manually.

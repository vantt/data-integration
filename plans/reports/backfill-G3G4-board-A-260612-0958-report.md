# Backfill G3+G4 Cards — Dashboard #103 Report

**Date:** 2026-06-12

---

## Cards Added

All 4 cards appended to **Tab 1 ("🎯 Hành động hôm nay")** in `customer_daily_action_queue.md`, after the existing Source and Freshness block (rows 22–30).

| Card ID | Name | Group | Display | Row | Col | Size |
|---------|------|-------|---------|-----|-----|------|
| 2306 | Gia tri rui ro theo loai hanh dong | G3 | row chart | 23 | 0 | 9×6 |
| 2307 | So luong khach theo loai hanh dong | G3 | row chart | 23 | 9 | 9×6 |
| 2308 | Upcoming Predicted Purchases — This Week | G4 | scalar | 30 | 0 | 9×3 |
| 2309 | Upcoming Predicted Purchases — This Month | G4 | scalar | 30 | 9 | 9×3 |

**Source blueprints:** G3 SQL from `customer_action_queue.md`; G4 SQL from `customer_retention_dashboard.md`.

**Filter wiring:** G3 wired `{{action_type}}` and `{{value_group}}` (exact match). G4 source used `{{segment}}` for value_group — rewired to `[[AND {{value_group}}]]` to match this board's filter slug.

---

## Deploy Tail

```
Dashboard 'Daily · Customer Action Queue [Retail]' exists (ID: 103)
Syncing 4 filter(s): Action Type, Value Group, Contactable, Next Purchase Signal
Dashboard has 2 tab(s): Hành động hôm nay, Watchlists
... (15 existing cards updated, 4 new cards updated) ...
Synced cards. Dashboard now has 34 cards.
Deployment Complete.
```

Return code: 0

---

## Collection ID Confirmation

`collection_id: 99` — confirmed post-deploy. Header `## 📂 Collection: Marketing & Customers > 👥 Customer` preserved intact.

---

## Per-Card Verification

| Card | Status | Rows | Sample |
|------|--------|------|--------|
| 2306 Gia tri rui ro | completed | 6 | 6 action types with VND values |
| 2307 So luong khach | completed | 6 | 6 action types with counts |
| 2308 Purchasing This Week | completed | 1 | 5 customers, LTV 21.3M, avg order 1.5M |
| 2309 Purchasing This Month | completed | 1 | 25 customers, LTV 143.6M, avg order 1.5M |

No errors on any card.

---

**Status:** DONE
**Summary:** 4 cards (G3: 2 row charts, G4: 2 scalars) added to Tab 1 of dashboard #103, collection_id remains 99, all cards execute cleanly with data.
**Concerns:** None.

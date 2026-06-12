# Backfill G2 — Board C (Dashboard #106) Report

**Date:** 2026-06-12

## Cards Added

Both cards inserted into **Tab: Behavior & Insights**, new "Acquisition" section at rows 53–60:

| Card | ID | Position | Viz |
|---|---|---|---|
| New Customers by Channel | 2304 | row 54, col 0, 9×6 | row chart |
| First-Order Revenue by Channel | 2305 | row 54, col 9, 9×6 | row chart |

Section header text card: "Identify acquisition channels — where do new customers come from?" at row 53.

## Deploy Tail

```
✅ Created Question 'New Customers by Channel' (ID: 2304)
✅ Created Question 'First-Order Revenue by Channel' (ID: 2305)
✅ Synced cards. Dashboard now has 54 cards.
🚀 Deployment Complete.
```

## Collection Confirm

`GET /api/dashboard/106` → `collection_id: 99` ✅ (unchanged)  
Total dashcards: 54 (was 52 before this deploy — +2 new cards + section header text = 54 total cards on dashboard)

## Verification

- Card 2304 `New Customers by Channel`: `result_metadata_count=2`, no error ✅
- Card 2305 `First-Order Revenue by Channel`: `result_metadata_count=2`, no error ✅

SQL reused verbatim from `customer_operational_dashboard.md` (Kenh & Dia ly tab, rows 477–564). Scope adapted from `scope_retail` → `scope_sales` per [Cross] target.

**Status:** DONE  
**Summary:** 2 acquisition-by-channel cards deployed to dashboard #106 Behavior & Insights tab; collection_id 99 intact; both cards load without error.  
**Concerns:** None.

# Backfill G1 Card — Board B (Dashboard #105) Report

**Date:** 2026-06-12

## Card Added

- **Name:** MAU vs Repeat-Buyer MAU (12M)
- **Card ID:** 2303 (newly created)
- **Tab:** Suc khoe Retention
- **Position:** row 28, col 0, size 18×6 (full-width, below Retention Health Scorecard)
- **SQL:** copied verbatim from `customer_operational_dashboard.md` lines 349–361 — uses `fact_orders + dim_customers`, `scope_retail`, 12-month window, `GROUP BY 1 ORDER BY 1`
- **Viz:** line chart, metrics MAU + MAU Repeat, colors #509EE3 / #7172AD

## Deploy Tail (key lines)

```
✅ Created Question 'MAU vs Repeat-Buyer MAU (12M)' (ID: 2303)
✅ Synced cards. Dashboard now has 42 cards.
🚀 Deployment Complete.
```

## Verification

| Check | Result |
|---|---|
| `collection_id` | **99** ✅ |
| Card present on dashboard | **Yes** (dashcard row 28, col 0) ✅ |
| Query rows returned | **11 months** (sample: 2025-07, MAU=2, MAU Repeat=2) ✅ |
| Query error | **None** ✅ |

Collection header `## 📂 Collection: Marketing & Customers > 👥 Customer` preserved intact.

---

**Status:** DONE  
**Summary:** Card "MAU vs Repeat-Buyer MAU (12M)" (ID 2303) added to Tab "Suc khoe Retention" at row 28 via blueprint edit + redeploy. Dashboard #105 confirmed in collection 99 with 42 total cards; query returns 11 rows, no error.  
**Concerns:** None.

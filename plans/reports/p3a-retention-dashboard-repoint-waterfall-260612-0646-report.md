# P3A: Retention Dashboard Repoint — Waterfall Model

**Date:** 2026-06-12  
**Dashboard:** #14 "Customer Retention & Lifecycle [Retail]" (collection 52)  
**Blueprint:** `docs/analytics-handbook/blueprints/customer_retention_dashboard.md`

---

## Pre-deploy Audit

- Fetched GET /api/dashboard/14 → 50 dashcards, 3 tabs (Suc khoe Retention, Phan tich Cohort, Hanh vi & Reactivation)
- Blueprint matches live exactly — no hand-made orphan cards found. All 25 question cards + 15 text cards + 10 "extra" live cards (Chu ky bao cao ×3, predictive signal cards ×5, Avg Order Value) are all already in blueprint.
- No regression risk identified.

---

## Change Made

Single card renamed + SQL replaced in blueprint (Tab: Suc khoe Retention, row 15, col 0, 9×6):

**Removed:** `Churn Rate Trend (6M)` (was card 303)
- Model: `mart_customer_status_snapshot_monthly`
- Only showed CHURNED %, survivorship-biased

**Added:** `Retention Waterfall Trend (6M)` (new card 2224)
- Model: `mart_retention_waterfall_monthly`
- Shows ACTIVE / AT_RISK / CHURNED counts, point-in-time, stacked area

**Before SQL (card 303):**
```sql
SELECT snapshot_month AS month,
  COUNT(CASE WHEN status='CHURNED' THEN 1 END) AS churned_customers,
  ROUND(COUNT(CASE WHEN status='CHURNED' THEN 1 END)*100.0/NULLIF(COUNT(*),0),1) AS "Churn Rate %"
FROM mart_customer_status_snapshot_monthly
WHERE snapshot_month >= (date_trunc('month',current_date) - INTERVAL '6 months' - INTERVAL '1 day')::date
  AND snapshot_month < date_trunc('month',current_date)::date
  [[AND value_group = {{segment}}]]
GROUP BY 1 ORDER BY 1
```

**After SQL (card 2224):**
```sql
SELECT snapshot_month AS month, status AS "Status", customer_count AS "Customers"
FROM mart_retention_waterfall_monthly
WHERE snapshot_month >= (date_trunc('month', current_date) - INTERVAL '6 months')::date
ORDER BY 1, 2
```

Viz changed from `line` (single metric) to `area` stacked (ACTIVE/AT_RISK/CHURNED).

---

## Deploy Output (tail)

```
✅ Updated all existing questions (IDs match by tab+name)
ℹ️  Question 'Retention Waterfall Trend (6M)' NOT found on tab — creating new
✅ Synced cards. Dashboard now has 50 cards.
🚀 Deployment Complete. RC: 0
```

---

## Post-deploy Verification

**GET /api/dashboard/14 → 50 dashcards (unchanged count)**

New card confirmed in dashboard:
- `card_id=2224` name=`Retention Waterfall Trend (6M)` tab=87 (Suc khoe Retention)
- Old card 303 (`Churn Rate Trend (6M)`) removed from layout

**Card query POST /api/card/2224/query:**

| snapshot_month | Status | Customers |
|---|---|---|
| 2026-05-31 | ACTIVE | 90 |
| 2026-05-31 | AT_RISK | 137 |
| 2026-05-31 | CHURNED | 993 |

Total rows: 18 (6 months × 3 statuses) — matches expected point-in-time data.  
Note: 2025-05 (ACTIVE=3) is outside the 6-month window as of 2026-06-12; verified separately via direct SQL query pre-deploy.

---

## Cards Left on mart_customer_status_snapshot_monthly

Legitimately still using old snapshot model (per-customer attributes, not trend):
- `Repeat Purchase Rate` (card 299) — scalar, orders_to_date column
- `Churn Rate` (card 964) — scalar, status column
- `Active Customer Rate` (card 965) — scalar, status column
- `Avg Order Value` (card 2223) — scalar, lifetime_value/orders_to_date
- `One-Time Buyer Rate` (card 978) — scalar, orders_to_date column

These use snapshot for MoM point-in-time scalars (valid use). No change needed.

---

## Follow-up Notes

- One-time-rate / M1-repeat scalar: blueprint already has `One-Time Buyer Rate` (card 978) using snapshot model scalar — not added to waterfall view as it's a different metric grain. Low-risk to add a waterfall-based ACTIVE rate scalar later.
- Old card 303 is now orphaned in Metabase (not on dashboard). Can archive manually if desired.

---

**Status:** DONE  
**Summary:** Replaced survivorship-biased Churn Rate Trend (6M) with point-in-time Retention Waterfall Trend (6M) using mart_retention_waterfall_monthly. Deployed via blueprint script, 50 cards intact, post-deploy query confirms ACTIVE=90/AT_RISK=137/CHURNED=993 for 2026-05.  
**Concerns:** None.

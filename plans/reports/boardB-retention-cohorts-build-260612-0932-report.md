# Board B — Weekly · Customer Retention & Cohorts [Retail] — Build Report

**Date:** 2026-06-12

---

## Blueprint

- **File:** `docs/analytics-handbook/blueprints/customer_retention_cohorts.md`
- **Collection header:** `## 📂 Collection: Marketing & Customers > 👥 Customer`

---

## Dashboard

| Field | Value |
|---|---|
| Dashboard ID | 105 |
| Name | Weekly · Customer Retention & Cohorts [Retail] |
| URL | https://bi.lan.fwg.vn/dashboard/105 |
| collection_id | **99** (👥 Customer — confirmed via GET /api/dashboard/105) |
| Tabs | Suc khoe Retention · Phan tich Cohort · Hanh vi & Reactivation |
| Total dashcards | 41 (24 question cards + 14 text cards + 3 Chu ky bao cao scalars) |

---

## Cards Deployed (by tab)

### Tab 1 — Suc khoe Retention (11 cards)
- #2254 Repeat Purchase Rate
- #2255 Churn Rate
- #2256 Avg Order Value
- #2257 Active Customer Rate
- #2244 Chu kỳ báo cáo (shared/updated)
- #2258 Customer Lifecycle Distribution
- #2259 Revenue by Lifecycle Status
- #2260 Segment x Status Matrix
- #2261 Retention Waterfall Trend (6M)
- #2262 Repeat Purchase Rate Trend (6M)
- #2263 Retention Health Scorecard

### Tab 2 — Phan tich Cohort (9 cards)
- #2244 Chu kỳ báo cáo (shared)
- #2264 Avg Month-1 Retention
- #2265 Best Cohort (M1 Retention)
- #2266 Avg Orders per Customer
- #2267 Returning Revenue Ratio
- #2268 Cohort Retention Heatmap
- #2269 Revenue by Cohort (Layer Cake)
- #2270 New vs Returning Revenue (6M)
- #2271 New vs Returning Customers (6M)

### Tab 3 — Hanh vi & Reactivation (7 cards)
- #2244 Chu kỳ báo cáo (shared)
- #2272 Avg Days Between Purchases
- #2273 Reactivated Customers (Last Month)
- #2274 One-Time Buyer Rate
- #2275 Purchase Frequency Distribution
- #2276 Days Between Purchases Distribution
- #2277 Reactivation Trend (6M)

---

## Dedup — Cards Removed vs Source #14

Removed 9 operational call-list cards (now live in Board A — Daily Action Queue):

| Removed Card | Reason |
|---|---|
| At-Risk Customer Watchlist | operational list |
| OVERDUE Customer Watchlist | operational list |
| At-Risk Customers Count | operational counter |
| OVERDUE Customers — Count and Value at Risk | operational counter |
| Next Purchase Signal by Segment | operational table |
| Upcoming Predicted Purchases — This Week | operational forecast |
| Upcoming Predicted Purchases — This Month | operational forecast |
| P3 text header ("Prioritize at-risk outreach...") | no longer relevant |
| P3 text header ("P3 Predictive signals...") | no longer relevant |

---

## Verification

| Check | Result |
|---|---|
| collection_id=99 | PASS — confirmed via API |
| 3 tabs present | PASS |
| Cohort Heatmap #2268 | OK — 11 rows, first: 2025-07 cohort, M0=100% |
| Waterfall Trend #2261 | OK — 18 rows, first: 2025-12-31 ACTIVE=25 |
| Repeat Purchase Rate #2254 | OK — 1 row: [25.5%, prev=26%] |
| Card errors | None |

---

## Deploy Tail (summary)

- 24 question cards created/updated, 17 text cards placed, 41 total dashcards synced
- No Binder Error or GROUP BY issues encountered
- `Chu kỳ báo cáo` shared card (#2244) updated 3× (once per tab — expected behavior)

---

**Status:** DONE
**Summary:** New dashboard #105 "Weekly · Customer Retention & Cohorts [Retail]" deployed to collection 99 (👥 Customer). 9 operational call-list cards removed vs source #14. All 3 verification card queries return data.
**Concerns:** None.

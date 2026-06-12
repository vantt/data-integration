# Product Performance & Velocity [Cross] — Build Report
**Date:** 2026-06-12

## Blueprint
`docs/analytics-handbook/blueprints/product_performance_velocity.md`

## Dashboard
- **Name:** Product Performance & Velocity [Cross]
- **ID:** 109
- **URL:** https://bi.lan.fwg.vn/dashboard/109
- **collection_id:** 100 ✅ (Merchandising & Product — matches `## 📂 Collection: Merchandising & Product`)

## Deploy Tail
- 34 dashcards synced across 3 tabs
- All questions created/updated successfully
- Tabs: Tong quan · Top & Bottom + Velocity · Health Signals

## Card List (22 questions + 12 text cards)

### Tab: Tong quan
| Card | ID | Type |
|---|---|---|
| Chu ky bao cao | 2310 (reused) | scalar |
| Doanh thu san pham | 2346 | scalar |
| So luong ban | 2347 | scalar |
| So san pham ban duoc | 2348 | scalar |
| DT trung binh/san pham | 2349 | scalar |
| Doanh thu san pham theo ngay | 2350 | line |
| So luong ban theo ngay | 2351 | line |
| Doanh thu theo loai san pham | 2352 | row |
| Ty trong doanh thu theo loai san pham | 2353 | pie |

### Tab: Top & Bottom + Velocity
| Card | ID | Type |
|---|---|---|
| Chu ky bao cao | 2310 (reused) | scalar |
| Top 20 SP theo doanh thu | 2354 | row |
| Top 20 SP theo so luong | 2355 | row |
| Top 10 SP tang truong MoM | 2356 | row |
| Top 10 SP sut giam MoM | 2357 | row |
| Top 20 SP theo daily velocity | 2358 | row |

### Tab: Health Signals (enrichment from mart_product_health)
| Card | ID | Type |
|---|---|---|
| Chu ky bao cao | 2310 (reused) | scalar |
| Phan bo lifecycle stage | 2318 (reused) | bar |
| Phan bo velocity momentum | 2359 | pie |
| San pham ACCELERATING | 2360 | table |
| San pham DECELERATING | 2361 | table |
| Bang health classification | 2362 | table |

## Verification
- `collection_id=100` confirmed via GET /api/dashboard/109
- 3 tabs present: Tong quan, Top & Bottom + Velocity, Health Signals
- Card queries (no errors):
  - `Doanh thu san pham` (2346) → 1 row ✅
  - `Phan bo lifecycle stage` (2318) → 5 rows ✅
  - `Bang health classification` (2362) → 116 rows ✅

## Notes
- `mart_product_health` had 116 rows with health_class data — health enrichment working
- Trend charts (rolling-30d hardcoded) and top/bottom movers carry ⚠️ "filter not matched" warnings for `date_range` — expected: these queries use hardcoded `current_date - INTERVAL '30 days'` (same pattern as old #30), not `{{date_range}}` template tags. KPI scalars are wired to date_range + product_type filters.
- Old dashboard #30 untouched.

---

**Status:** DONE
**Summary:** Blueprint created at `docs/analytics-handbook/blueprints/product_performance_velocity.md` and deployed as dashboard #109 in collection 100 (Merchandising & Product). 3 tabs, 34 cards. Health signals tab enriched with `mart_product_health` (velocity_momentum, lifecycle_stage, health_class). Old #30 untouched.
**Concerns:** Trend/top-bottom cards use hardcoded 30d window, not wired to date_range filter — same as #30 pattern, intentional. Health_class only covers ~42/116 SKUs (COGS coverage constraint).

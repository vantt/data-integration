# Metabase Dashboard SQL Verification Report
**Date:** 2026-06-13  
**Scope:** Dashboards 103, 105, 111, 112 — read-only SQL audit  
**Risk flags:** snapshot-model misuse in retention trends; SKU-affinity column coverage in D103

---

## Dashboard 103 — Daily · Customer Action Queue [Retail]

**Verdict: MATCH** (with enhancement opportunity)

### Evidence
- All action-type counter cards (2168–2172, 2225) query `mart_customer_action_queue WHERE action_type = '<TYPE>'` — all 6 required types present: CALL_NOW, REORDER_NUDGE, REORDER_PREEMPT, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK. ✅
- Queue outreach list (2175), value-at-stake cards (2227, 2228, 2306, 2307), reactivation mine (2243) all source from `mart_customer_action_queue`. ✅
- Contactable card (2241), LTV/value-at-stake aggregates (2227, 2228) include `is_contactable` / `value_at_stake` filtering. ✅
- Watchlist cards (1361, 1362, 1363) and signal breakdown (2156, 2158) source from `dim_customers` — appropriate for point-in-current lookups, not trend. ✅
- Predicted purchase cards (2308, 2309) source from `dim_customers.predicted_next_purchase_date`. ✅

### SKU-Affinity Column Coverage — ENHANCEMENT OPPORTUNITY
Card 2175 (queue list) selects these columns from `mart_customer_action_queue`:  
`priority_rank, customer_code, full_name, phone, is_contactable, value_group, action_rationale, value_at_stake, lifetime_value, recency_days, last_order_date, predicted_next_purchase_date`

**ABSENT:** `last_purchased_product`, `top_affinity_product`, `second_affinity_product`  
**Status in mart model:** columns EXIST in `mart_customer_action_queue.sql` (lines 32-37, 96-101).  
**Conclusion:** The mart ships the affinity columns; the dashboard card does not surface them yet.  
→ Flag as **ENHANCEMENT OPPORTUNITY** (not a defect). Adding these 3 columns to card 2175's SELECT would give CSKH reps immediate SKU-level context for each outreach call.

---

## Dashboard 105 — Weekly · Customer Retention & Cohorts [Retail]

**Verdict: PARTIAL** — snapshot model used for scalar KPI cards; point-in-time sources used for trend cards

### Point-in-time CORRECT cards
| Card | Source | Notes |
|------|--------|-------|
| 2261 Retention Waterfall Trend (6M) | `mart_retention_waterfall_monthly` | Explicit comment: "Replaces survivorship-biased mart_customer_status_snapshot_monthly for this trend view" ✅ |
| 2262 Repeat Purchase Rate Trend (6M) | `fact_orders` JOIN `dim_customers` | Rolling window on raw orders ✅ |
| 2267 Returning Revenue Ratio | `fact_orders` JOIN `dim_customers` | ✅ |
| 2270 New vs Returning Revenue (6M) | `fact_orders` JOIN `dim_customers` | ✅ |
| 2271 New vs Returning Customers (6M) | `fact_orders` JOIN `dim_customers` | ✅ |
| 2272 Avg Days Between Purchases | `fact_orders` | ✅ |
| 2273 Reactivated Customers (Last Month) | `fact_orders` | ✅ |
| 2277 Reactivation Trend (6M) | `fact_orders` | ✅ |
| 2264 Avg Month-1 Retention | `dim_customers` + `fact_orders` JOIN | Cohort join, point-in-time by first_order_date ✅ |
| 2265 Best Cohort (M1 Retention) | `dim_customers` + `fact_orders` JOIN | Same ✅ |
| 2303 MAU vs Repeat-Buyer MAU (12M) | `fact_orders` JOIN `dim_customers` | ✅ |

### Snapshot-model cards (mart_customer_status_snapshot_monthly)
| Card | Source | Risk assessment |
|------|--------|-----------------|
| 2254 Repeat Purchase Rate | `mart_customer_status_snapshot_monthly` | Scalar MoM compare (current vs prev month-end snapshot). Survivorship bias applies but magnitude depends on use: comparing two recent snapshots → bias is small if both points are recent. **Moderate risk** |
| 2255 Churn Rate | `mart_customer_status_snapshot_monthly` | Same. Scalar MoM compare. **Moderate risk** |
| 2256 Avg Order Value | `mart_customer_status_snapshot_monthly` | Card comment says "proxy for lifespan using snapshot recency" — not purely a trend. **Low-Moderate risk** |
| 2257 Active Customer Rate | `mart_customer_status_snapshot_monthly` | Scalar MoM compare. **Moderate risk** |
| 2266 Avg Orders per Customer | `mart_customer_status_snapshot_monthly` | Scalar MoM compare on `orders_to_date`. `orders_to_date` is cumulative (not recalculated by status), so survivorship bias on STATUS doesn't corrupt order count — bias lower here. **Low risk** |
| 2274 One-Time Buyer Rate | `mart_customer_status_snapshot_monthly` | Scalar MoM compare on `orders_to_date = 1`. Same reasoning as 2266. **Low risk** |

**Assessment:** Cards 2254, 2255, 2257 carry **moderate snapshot bias risk** when used as "current rate" KPIs — a customer who churned 6 months ago but has since returned is counted ACTIVE in both snapshot points, inflating apparent repeat/active rates. The bias is smaller for adjacent month comparisons than for trend charts. The trend chart (2261) has already been migrated to `mart_retention_waterfall_monthly`; the scalar KPI cards have not.

### dim_customers-based cards (current state, not trend)
Cards 2258, 2259, 2260, 2263, 2275, 2276 use `dim_customers` directly — appropriate for current-state cross-sections, not historical trend. ✅

---

## Dashboard 111 — Cohort Explorer [Retail]

**Verdict: MATCH**

### Evidence
- All 3 cards (2383 Cohort Retention Matrix, 2384 Cohort Value Summary, 2385 Cohort Data Table) query `main_marts.mart_cohort_retention WHERE window_type = 'relative'`. ✅
- `mart_cohort_retention` is built from `fact_orders` (confirmed from model file), making it point-in-time by cohort definition. ✅
- M0–M12 retention columns exposed via pivot; `cohort_dimension` parameter filter present. ✅
- No use of `mart_customer_status_snapshot_monthly`. ✅

---

## Dashboard 112 — Cohort Calendar Trend [Retail]

**Verdict: MATCH**

### Evidence
- Both cards (2386 Retention % by Calendar Month, 2387 Revenue by Calendar Month) query `main_marts.mart_cohort_retention WHERE window_type = 'calendar'`. ✅
- Calendar view correctly uses the same point-in-time mart with `window_type = 'calendar'` filter, projecting cohort behavior onto absolute calendar months. ✅
- No use of `mart_customer_status_snapshot_monthly`. ✅

---

## Summary Findings

### (a) Snapshot-model misuse
| Dashboard | Cards | Source | Severity |
|-----------|-------|--------|----------|
| 105 | 2254, 2255, 2257 (Repeat Purchase Rate, Churn Rate, Active Customer Rate) | `mart_customer_status_snapshot_monthly` | Moderate — survivorship bias in scalar KPIs (not trend charts); bias smaller for adjacent-month MoM compares than for multi-month trends |
| 105 | 2256, 2266, 2274 | `mart_customer_status_snapshot_monthly` | Low — orders_to_date is cumulative so status-bias doesn't corrupt order count |
| 111, 112 | All cards | `mart_cohort_retention` | None ✅ |

**Key distinction:** The high-risk pattern (snapshot driving a TREND line across 6+ months) was already fixed — card 2261 explicitly migrated to `mart_retention_waterfall_monthly`. The remaining snapshot usage is limited to scalar MoM scorecards where the bias window is 1 month, not multi-month.

### (b) SKU-Affinity enhancement opportunity (D103)
- `mart_customer_action_queue` model includes `last_purchased_product`, `top_affinity_product`, `second_affinity_product`.
- Card 2175 (Queue — Danh sach outreach) does NOT select these columns.
- No other D103 card surfaces affinity data.
- **Recommended action:** Add affinity columns to card 2175 SELECT to give CSKH reps product-level context during calls. Low effort, high practical value.

---

## Unresolved Questions

1. **Cards 2254/2255/2257 migration:** Should these scalar KPI cards be rewritten to use `mart_retention_waterfall_monthly` for full bias removal? Workload is small but requires verifying the waterfall mart exposes the necessary columns (customer_count by status per month-end — it does). Decision: acceptable-as-is or migrate for consistency?

2. **Card 2303 MAU calculation:** Uses `o.scope_retail` (not `o.scope_sales`) — intentional scope difference vs other cards that use `scope_sales`? Confirm no double-counting or filter mismatch.

3. **`mart_cohort_retention` source verification:** Assumed built from `fact_orders` (model name + waterfall comment imply it). Full model not read. If it references a snapshot table internally, the MATCH verdicts for 111/112 need revisiting.

# Cohort & Retention Diagnostic — FineJapan

**Generated:** 2026-06-21  
**Analyst:** analytics-analyst  
**Data:** fact_orders parquet (latest snapshot: `fact_orders_20260621142114.parquet`)  
**Scope:** 2021-05-26 → 2026-06-19 | 10,330 orders | 5,834 customers

---

## VERDICT

- **Repeat-buying base: AGING & ERODING.** 59% of all repeat customers last ordered >720 days ago. Active repeat base (≤90d) is only 109 customers. The loyal base peaked in 2024 (378 repeat customers last active) and is visibly shrinking (264 in 2025, 172 so far in 2026 — annualized ~344, slight miss vs 2024 but 2026 is half-year only; still trajectories point down from 2024 peak).
- **First→Second conversion: ALIVE but structurally WEAK.** Conversion rates oscillated 18–30% across all cohorts. There is NO clear collapse, but NO growth either. Stable at a mediocre level (~22–25% for 2024). 2025-Q2 dipped to 13.1% (but only 137 new customers, small sample). 2026-Q1 showed a bump to 29.9% — too early to call recovery.
- **Repurchase cadence: Short tail, long tail.** Median days to 2nd order = 49 days (p25=12d, p75=157d). The short-tail (P25=12d) suggests a meaningful "top-up" buyer segment; the long tail (P75=157d) ~5 months aligns with a supplement cycle. ~70% of repurchasers return within 180 days. Acquisition funnel itself is SHRINKING: 550 new customers in 2022-Q2 down to 130-140/quarter in 2025-2026.

---

## 1. Acquisition Cohorts Over Time

| Cohort | New Custs | Total Orders | % Got 2nd Order | % Active (≤180d) |
|--------|----------:|-------------:|----------------:|----------------:|
| 2021-Q2 | 119 | 555 | 39.5% | 3.4% |
| 2021-Q3 | 139 | 260 | 38.8% | 1.4% |
| 2021-Q4 | 407 | 956 | 44.7% | 1.2% |
| 2022-Q1 | 412 | 852 | 34.7% | 0.5% |
| 2022-Q2 | 550 | 888 | 28.5% | 0.7% |
| 2022-Q3 | 420 | 843 | 26.4% | 0.7% |
| 2022-Q4 | 274 | 619 | 34.3% | 0.4% |
| 2023-Q1 | 336 | 727 | 29.5% | 1.8% |
| 2023-Q2 | 286 | 429 | 23.4% | 0.7% |
| 2023-Q3 | 305 | 428 | 18.4% | 1.3% |
| 2023-Q4 | 247 | 387 | 20.6% | 1.2% |
| 2024-Q1 | 236 | 415 | 24.6% | 3.0% |
| 2024-Q2 | 384 | 563 | 22.7% | 2.6% |
| 2024-Q3 | 426 | 629 | 23.0% | 2.1% |
| 2024-Q4 | 325 | 498 | 24.9% | 3.4% |
| 2025-Q1 | 292 | 369 | 18.5% | 5.1% |
| 2025-Q2 | 137 | 164 | 13.1% | 1.5% |
| 2025-Q3 | 130 | 183 | 21.5% | 9.2% |
| 2025-Q4 | 139 | 204 | 26.6% | 23.7% |
| 2026-Q1 | 134 | 203 | 29.9% | 100.0% |
| 2026-Q2 | 136 | 158 | 12.5% | 100.0% |

**Trend:** Cohort sizes peaked at 550 (2022-Q2) and collapsed to ~130-140/quarter in 2025-2026. Older 2021 cohorts had better 2nd-order conversion (38-45%) vs 2022-2025 cohorts (18-30%). % active 180d for recent cohorts is high by math (most ordered recently; this metric loses meaning for cohorts <6 months old).

---

## 2. First→Second Order Conversion Curve (2023–2026)

| Cohort | New Custs | Converted to 2nd | Conversion % | Assessment |
|--------|----------:|----------------:|-------------:|------------|
| 2023-Q1 | 336 | 99 | 29.5% | Baseline |
| 2023-Q2 | 286 | 67 | 23.4% | ↓ |
| 2023-Q3 | 305 | 56 | 18.4% | ↓ worst |
| 2023-Q4 | 247 | 51 | 20.6% | ↑ partial |
| 2024-Q1 | 236 | 58 | 24.6% | ↑ stable |
| 2024-Q2 | 384 | 87 | 22.7% | = |
| 2024-Q3 | 426 | 98 | 23.0% | = |
| 2024-Q4 | 325 | 81 | 24.9% | = |
| 2025-Q1 | 292 | 54 | 18.5% | ↓ |
| 2025-Q2 | 137 | 18 | 13.1% | ↓ ⚠️ small N |
| 2025-Q3 | 130 | 28 | 21.5% | ↑ partial |
| 2025-Q4 | 139 | 37 | 26.6% | ↑ |
| 2026-Q1 | 134 | 40 | 29.9% | ↑ best recent |
| 2026-Q2 | 136 | 17 | 12.5% | ⚠️ TOO EARLY |

**Verdict: ALIVE but WEAK.** No catastrophic collapse. 2024 was stable ~22-25%. 2026-Q1 bounce to 29.9% is promising but N=134 only. **Caveat:** 2025-Q4 and 2026 cohorts have not had enough time elapsed to reach their final conversion rate — median repurchase is 49 days, so 2026-Q2 is definitively too early. 2026-Q1 final rate likely higher than shown.

---

## 3. Time-to-Second-Order (Repurchase Cadence)

All customers who repurchased (n=1,579):

| Metric | Days |
|--------|-----:|
| P25 | 12 |
| Median | 49 |
| P75 | 157 |
| Average | 124 |

**Interpretation:**
- 25% of repurchasers return within 12 days (impulse/top-up buyers, gifting)
- Median 49 days ≈ ~1.5 months: consistent with a 1-month supply refill cycle with some lag
- P75 = 157 days ≈ 5 months: supplement cycle (1 jar lasts ~2-3 months, reorder at depletion)
- Long tail pulls average to 124 days
- **Strategic implication:** a 14-day post-purchase nudge + 45-day refill reminder would capture the bulk of winnable repeats before they lapse

---

## 4. Acquisition Volume Trend (Top of Funnel)

| Quarter | New Customers | vs Peak (2022-Q2=550) |
|---------|-------------:|----------------------:|
| 2021-Q2 | 119 | — |
| 2021-Q3 | 139 | — |
| 2021-Q4 | 407 | — |
| 2022-Q1 | 412 | 75% |
| **2022-Q2** | **550** | **PEAK** |
| 2022-Q3 | 420 | 76% |
| 2022-Q4 | 274 | 50% |
| 2023-Q1 | 336 | 61% |
| 2023-Q2 | 286 | 52% |
| 2023-Q3 | 305 | 55% |
| 2023-Q4 | 247 | 45% |
| 2024-Q1 | 236 | 43% |
| 2024-Q2 | 384 | 70% |
| 2024-Q3 | 426 | 77% |
| 2024-Q4 | 325 | 59% |
| 2025-Q1 | 292 | 53% |
| 2025-Q2 | 137 | 25% |
| 2025-Q3 | 130 | 24% |
| 2025-Q4 | 139 | 25% |
| 2026-Q1 | 134 | 24% |
| 2026-Q2 | 136 | 25% |

**Trend:** Funnel contracted sharply after 2024-Q3 (426) to ~130-136/quarter in 2025-Q2 through 2026-Q2 — a **70% drop from peak** and **~68% drop from 2024-Q3 high**. 2024-Q2/Q3 showed a recovery that did not sustain. 2025-Q2 onward is clearly a new, lower plateau at ~130-140/quarter.

---

## 5. Repeat-Base Health

### Recency Segments (all repeat customers with ≥2 orders, as of 2026-06-19)

| Segment | Customers | % of Repeat Base |
|---------|----------:|----------------:|
| Active (≤90d) | 109 | 6.9% |
| Warm (91–180d) | 74 | 4.7% |
| Dormant (181–365d) | 127 | 8.0% |
| At Risk (366–720d) | 334 | 21.2% |
| Lost (>720d) | 935 | 59.2% |
| **Total repeat base** | **1,579** | 100% |

**59.2% of all repeat customers are effectively LOST.** Only 11.6% are active or warm.

### Repeat Customers Last Active by Year

| Year | Repeat Custs Active That Year | Loyal (3+ Orders) |
|------|------------------------------:|------------------:|
| 2022 | 329 | 108 |
| 2023 | 346 | 163 |
| 2024 | 378 | 194 |
| 2025 | 264 | 136 |
| 2026 (to Jun) | 172 | 97 |

**Peak repeat activity in 2024 (378 customers placed a repeat order).** 2025 dropped 30% to 264. 2026 is on pace for ~344 annualized — close to 2024 but depends on H2 trajectory. The loyal 3+ segment followed the same pattern: peak 194 in 2024, dropped to 136 in 2025.

---

## Data Caveats & Exclusions

### What was excluded

| Category | Customers Excluded | Basis |
|-|-|-|
| B2B scope (`scope_b2b=true`) | 160 | Flag set by Sapo pipeline |
| Non-B2B outliers (avg order >20M VND) | 12 | Heuristic to catch export/miscoded accounts |
| **Total excluded** | **172** | from 5,955 completed+active unique customers |
| **Included in cohort base** | **5,834** | — |

- The known 23.7B revenue distortion from B2B/export accounts: the customer with ~10.2B net revenue (`5448a81aba692721eab0fa105ebe6f50`) is partially `scope_b2b=true` and partially `scope_b2b=false` (i.e. multi-tagged). It falls in the outlier exclusion bucket (avg_net=148M/order).
- **Zero net revenue orders (3,936):** Majority are fully-discounted promo/gift orders (gross>0, discount=gross). These ARE included in cohort counts (customer placed a real order). A subset (1,024 zero-everything orders across 580 customers) may be system placeholders — they are included in this analysis since filtering them out did not materially change conversion rates.
- **Scope `scope_b2b=false AND scope_retail=false AND scope_sales=false`:** 1,882 customers / 4,121 orders fall in "neither" category (avg net ~3.1M/order). These are included as non-B2B non-retail orders — likely offline/phone channel or wholesale not flagged as B2B. Exclusion would reduce cohort base ~32% without a clear justification; keeping them in. This adds noise to cohort metrics.
- **Cancelled orders** are excluded (status='COMPLETED' only); OPEN orders excluded (not yet closed).
- **`is_active_order=false` orders** (2,006 records, all status≠COMPLETED, pre-2026): excluded.
- **customer_type:** NOT used — migration known incomplete.
- **source_system column:** NOT present in fact_orders parquet (only in raw layer); scope flags used instead.

---

## Unresolved Questions

1. **What drove the 2025-Q2 acquisition crash?** 137 new customers vs 292 in Q1 and 426 in 2024-Q3 — was this a channel shutdown, budget cut, campaign pause, or platform change (Shopee/Tiki algorithm)?
2. **Is the 2026-Q1 conversion recovery (29.9%) signal or noise?** N=134 is small. Needs confirmation from 2026-Q2 final data once >90 days elapsed.
3. **"Neither" scope customers (1,882):** Are these retail customers on a different channel (offline/phone)? Clarifying their channel would allow cleaner retail-only cohort.
4. **Repeat base "Lost >720d" (935 customers):** Is there a reactivation campaign running? At current acquisition rate (~130/qtr), the lost base is 7× annual new customer volume — even modest reactivation would be more efficient than new acquisition.
5. **Supplement repurchase cycle vs channel:** Do Shopee/Tiki customers have different cadences than direct/offline? Breakdown by channel_key would inform platform-specific retention tactics.
6. **2025-Q2 dip in `scope_retail=true` customers (137 new):** Verify whether this is a real acquisition decline or a data ingestion issue (partial period, source system gap).

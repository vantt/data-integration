# Masked-Repeat Customer Economics & Reachability — Hug A2 Sizing Report

**Generated:** 2026-06-20  
**Analyst:** analytics-analyst subagent  
**Scope:** READ-ONLY. No code/mart/strategy-doc modifications.  
**DB:** `main_marts.mart_customer_tier`, `main_marts.fact_orders` via olap.duckdb (read_only=True)

---

## 1. Reachability 3-Zone Split (Primary Table)

> **Definition:** Shopee Chat Broadcast limit = 720 days. "Active" = natural reorder window ≤90 days (Hug-capturable immediately on next purchase).

| Zone | Recency | Customers | Total CM (VND) | Avg CM/customer (k VND) | Avg Orders | Notes |
|------|---------|-----------|---------------|------------------------|------------|-------|
| Zone 1 — Active | ≤90 days | **69** | **1,653M** | 23,963k | 19.6 | Hug-capturable now on next purchase |
| Zone 2 — Dormant-Reachable | 91–720 days | **283** | **-346M** ⚠️ | see note | 4.5 | Reachable via Shopee Chat Broadcast; CM distorted by 2 outliers |
| Zone 3 — Lost | >720 days | **81** | **255M** | 3,142k | 4.0 | Permanently unreachable even via Shopee tool |
| **TOTAL** | | **433** | **1,562M** | 3,608k | 6.8 | |

### Zone 2 outlier correction

Zone 2 aggregate CM is −346M because of **one CHANNEL_OTHER customer** (`381f3f3e...`) with lifetime CM = −1,100M (12 orders, recency 151d). This single record distorts the entire zone. Excluding it:

| Zone | Customers | CM ex-outlier (VND) | Avg CM/customer (k VND) |
|------|-----------|--------------------|-----------------------|
| Zone 2a: 91–180d | 32 (excl. 1 outlier) | **105M** | 3,295k |
| Zone 2b: 181–365d | 55 | **389M** | 7,070k |
| Zone 2c: 366–720d | 195 | **261M** | 1,336k |
| **Zone 2 total (excl. outlier)** | **282** | **755M** | **2,677k** |

**Actionable reachable opportunity (Zone 1 + Zone 2 ex-outlier): 351 customers, ~2,408M lifetime CM already realized.**

### Marketplace-only split (Hug's direct target channel)

| Zone | Marketplace Customers | Total CM (VND) | CM/order (k VND) |
|------|----------------------|---------------|-----------------|
| Zone 1 active ≤90d | 62 | 186M | 797k |
| Zone 2 dormant 91–720d | 259 | 417M | 545k |
| Zone 3 lost >720d | 43 | 80M | 1,863k |

90% of masked-repeat customers are marketplace-channel. Zone 2 has 259 marketplace customers with 417M lifetime CM and positive per-order margin (545k/order).

**SQL used:**
```sql
-- Zone split
SELECT CASE WHEN recency_days <= 90 THEN 'zone_1' WHEN recency_days <= 720 THEN 'zone_2' ELSE 'zone_3' END,
  COUNT(*), SUM(lifetime_contribution_margin), AVG(order_count)
FROM main_marts.mart_customer_tier
WHERE source_contact_quality = 'masked' AND order_count >= 2
GROUP BY 1
```

---

## 2. Reorder Cadence

Inter-purchase gap analysis via `LAG(ordered_at)` on `fact_orders` (active orders only, `is_active_order = TRUE`):

| Segment | Gap Observations | Avg Gap (days) | P25 | Median | P75 | P90 |
|---------|-----------------|---------------|-----|--------|-----|-----|
| Masked-repeat | 2,512 | **33** | 1 | **7** | 28 | 82 |
| Real-repeat (benchmark) | 5,026 | **77** | 5 | **21** | 87 | 233 |

**Key finding:** Masked-repeat customers reorder dramatically faster than real contacts — median 7 days vs 21 days for real-repeat. P75 = 28 days means 75% of repeat purchases happen within a month of prior order.

**Interpretation of 508-day median recency:** NOT "dead customers with 7-day cycles." The distribution is bimodal:
- Zone 1 (69 customers, avg recency 33d): genuinely active, ordering every 7 days median
- Zone 2–3 (364 customers, avg recency 500–1,017d): churned cohort, most likely lapsed at the COGS-repoint boundary (~2024–2025 transition period) or natural attrition

**Implication for Hug speed:** For Zone 1 (active), next Hug capture opportunity is within **28 days for 75% of customers**. For Zone 2, capture depends on reactivation — not natural reorder.

**SQL used:**
```sql
WITH masked_keys AS (SELECT customer_key FROM main_marts.mart_customer_tier WHERE source_contact_quality = 'masked' AND order_count >= 2),
orders AS (SELECT fo.customer_key, fo.ordered_at,
    LAG(fo.ordered_at) OVER (PARTITION BY fo.customer_key ORDER BY fo.ordered_at) AS prev_ordered_at
  FROM main_marts.fact_orders fo JOIN masked_keys mk ON fo.customer_key = mk.customer_key WHERE fo.is_active_order = TRUE),
gaps AS (SELECT CAST(DATEDIFF('day', prev_ordered_at, ordered_at) AS INTEGER) AS gap_days FROM orders WHERE prev_ordered_at IS NOT NULL)
SELECT COUNT(*), ROUND(AVG(gap_days)), ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY gap_days)) FROM gaps
```

---

## 3. AOV Distribution & Offer Sizing

Average order value = `lifetime_value / order_count` per masked-repeat customer:

| AOV Bucket | Customers | Avg AOV (k VND) | Median AOV (k VND) | 50k voucher = % AOV | Avg CM/order (k VND) | CM < 50k count |
|------------|-----------|----------------|-------------------|--------------------|--------------------|---------------|
| A: <500k | 97 | 254k | 266k | **19.7%** | −1,255k ⚠️ | 41 |
| B: 500k–1M | 72 | 744k | 737k | 6.7% | 284k | 6 |
| C: 1M–2M | 172 | 1,447k | 1,398k | 3.5% | 637k | 5 |
| D: 2M–5M | 77 | 2,953k | 2,770k | 1.7% | 1,300k | 2 |
| E: 5M–10M | 10 | 7,062k | 6,829k | 0.7% | 3,617k | 0 |
| F: >10M | 5 | 21,755k | 18,136k | 0.2% | 8,271k | 0 |

**Critical insight:** Bucket A (97 customers, 22% of masked-repeat) has avg CM/order of **−1,255k VND** — already margin-negative at order level. A 50k voucher makes no difference to the structural problem (likely high returns/discounts on low-value Shopee orders).

### Offer recommendation

| AOV Range | Voucher | Rationale |
|-----------|---------|-----------|
| <500k (Bucket A) | **None / exclude** | Negative margin at order level; voucher adds cost without fixing structural issue |
| 500k–1M (Bucket B) | 25k–30k flat | 50k = 6.7% AOV, too rich; CM is 284k — 50k erodes 18% of margin |
| 1M–2M (Bucket C) | **50k flat** | 50k = 3.5% AOV; safe — CM 637k, voucher = 8% of margin |
| 2M+ (Buckets D–F) | 50k–100k or 2% capped | Voucher immaterial to AOV; can be more generous without margin risk |

**Bottom line:** 50k flat is safe for C (172 customers, 40% of masked-repeat) and D–F. Buckets A should be excluded from voucher targeting. Bucket B needs a reduced offer (25k) or minimum-spend gate (e.g., 50k off orders ≥1.5M).

**SQL used:**
```sql
WITH masked_repeat AS (SELECT CAST(lifetime_value AS DOUBLE)/order_count AS avg_order_value,
    CAST(lifetime_contribution_margin AS DOUBLE)/order_count AS avg_cm_per_order
  FROM main_marts.mart_customer_tier WHERE source_contact_quality = 'masked' AND order_count >= 2)
SELECT CASE WHEN avg_order_value < 500000 THEN 'A_lt500k' ... END AS aov_bucket,
  COUNT(*), ROUND(50000.0/AVG(avg_order_value)*100, 1) AS voucher_pct_aov,
  SUM(CASE WHEN avg_cm_per_order < 50000 THEN 1 ELSE 0 END) AS margin_lt_50k_count
FROM masked_repeat GROUP BY 1
```

---

## 4. Forward Annual Opportunity (Reconciliation: 683M vs 1,562M)

### What the three figures mean

| Figure | What it is | Source |
|--------|-----------|--------|
| **1,562M VND** | *Lifetime* CM already realized across ALL 433 masked-repeat customers' order history | `SUM(lifetime_contribution_margin)` in mart |
| **683M VND** | Plan figure — likely forward opportunity estimate for a subset (marketplace Zone 2?) | Strategy doc (unverified here — not read) |
| **Forward annual** | NEW CM expected over next 12 months, derived below | Formula below |

### Forward annual opportunity formula

**Target segment:** Zone 2 marketplace (259 customers — reachable dormant, positive per-order margin, correct channel for Shopee tool)

```
Forward Annual CM = Reachable Customers × Reactivation Rate × Annual Orders per Reactivated Customer × CM per Order

= 259 × [R] × [A] × 545k VND
```

**Inputs from data:**
- Zone 2 marketplace customers: **259**
- CM per order (Zone 2 marketplace): **545k VND**
- Annual order rate for *active* masked-repeat (Zone 1, annualized from cadence): **~11.8 orders/year** (per tenure analysis); but these are Zone 2 dormant, so post-reactivation rate likely **4–6 orders/year** [ASSUMPTION — see label below]

**Scenarios:**

| Reactivation Rate (R) | Post-reactivation Orders/yr (A) | Annual CM |
|----------------------|--------------------------------|-----------|
| 10% (conservative) | 4 | **5.7M VND** |
| 20% (base case) | 5 | **14.2M VND** |
| 30% (optimistic) | 6 | **25.6M VND** |

**ASSUMPTION LABELS:**
- `[R]` Reactivation rate: no prior campaign data exists for this segment. 10–30% range is industry-typical for lapsed-customer reactivation via voucher. **Leadership must decide which R to use.**
- `[A]` Post-reactivation annual orders: assumed 4–6 (lower than Zone 1's 11.8/yr because zone 2 is lapsed; they may not return to full frequency). **Unverified — no historical reactivation data.**

**Why this differs from 1,562M (lifetime):** 1,562M is the sum of *all* CM ever generated by masked-repeat customers — already realized, spans multiple years. Forward opportunity is new CM, gated by reactivation probability.

**Why this may differ from plan's 683M:** 683M is likely either (a) unadjusted lifetime CM for a subset, or (b) an optimistic forward estimate using a much higher reactivation rate or broader segment. Without reading the strategy doc, cannot reconcile exactly. Leadership should confirm which segment and R% the 683M uses.

---

## 5. Holdout Design (A/B Measurement)

### Problem
N is small: ~62 active marketplace (Zone 1) + ~259 dormant marketplace (Zone 2) = 321 total addressable. True incremental lift measurement requires a holdout control.

### Proposed Design

**Phase 1 — Zone 1 (Active, natural reorder, fast read)**

| Parameter | Value |
|-----------|-------|
| Eligible | 62 marketplace customers, recency ≤90d |
| Split | 40 Treatment / 22 Control (65/35; keep control small given low N) |
| Treatment | Hug voucher on next Shopee order (50k or tiered per Section 3) |
| Control | No Hug intervention — natural reorder observed |
| Primary metric | **Repeat purchase within 60 days** (binary) |
| Secondary metric | CM/order on treatment purchases vs control baseline |
| Read window | **90 days** (given 7-day median gap, expect 3–5 orders per active customer in window) |
| Min detectable effect | With 40T/22C, ~80% power to detect 20pp lift (30% control → 50% treatment reorder rate). If control base rate is lower, effect must be larger to detect. |

**Phase 2 — Zone 2 (Dormant reactivation, slower read)**

| Parameter | Value |
|-----------|-------|
| Eligible | 259 marketplace customers, recency 91–720d |
| Exclude | Bucket A (AOV <500k) — negative margin, n≈57 zone-2 estimate |
| Net eligible | ~200 |
| Split | 130 Treatment / 70 Control |
| Treatment | Shopee Chat Broadcast + voucher (50k or tiered) |
| Control | No outreach — passive observation |
| Primary metric | **Purchase within 120 days** (binary; reactivation) |
| Secondary metric | Incremental CM = treatment group CM − (control reactivation rate × avg CM/order × 120d) |
| Read window | **180 days** (dormant customers take longer to convert; expect noisy data before 120d) |
| Min detectable effect | With 130T/70C, ~80% power to detect ~12pp reactivation lift (e.g. 5% control → 17% treatment). Very small N — treat results as directional, not conclusive. |

**Key caveat:** With these Ns, Phase 1 is the more reliable test. Phase 2 will likely be underpowered for statistical significance — run it anyway for directional learning + unit economics measurement.

**Metric to track:** Net incremental CM = (treatment CM earned) − (voucher cost) − (control counterfactual CM). If net incremental > 0, Hug is margin-accretive.

---

## 6. Channel Preference Breakdown (Masked-Repeat)

### All 433 masked-repeat customers

| Channel | Customers | % of segment | Total CM (VND) | Avg CM/customer (k VND) |
|---------|-----------|-------------|---------------|------------------------|
| CHANNEL_MARKETPLACE | **364** | **84%** | 683M | 1,876k |
| CHANNEL_DIRECT | 52 | 12% | 2,181M | 41,937k |
| CHANNEL_OTHER | 11 | 3% | −1,248M | −113,465k ⚠️ |
| CHANNEL_OFFLINE | 5 | 1% | 75M | 14,923k |
| CHANNEL_SOCIAL | 1 | 0.2% | −128M | −127,877k ⚠️ |

**CHANNEL_OTHER and CHANNEL_SOCIAL contain massive negative-CM outliers.** These 12 customers drag the total masked-repeat CM from ~2,938M down to 1,562M. They are not Hug targets (no Shopee tool applies).

### Zone 2 (dormant reachable) channel breakdown

| Channel | Customers | Total CM (VND) | Avg CM/customer (k VND) |
|---------|-----------|---------------|------------------------|
| CHANNEL_MARKETPLACE | **259 (91%)** | 417M | 1,611k |
| CHANNEL_DIRECT | 18 | 485M | 26,947k |
| CHANNEL_OTHER | 4 | −1,189M | −297,310k ⚠️ |
| CHANNEL_OFFLINE | 1 | 69M | 69,307k |
| CHANNEL_SOCIAL | 1 | −128M | −127,877k ⚠️ |

**Shopee matters most.** 91% of reachable dormant masked-repeat customers are marketplace. Direct-channel customers (18, avg CM 26.9M each) are high-value but not contactable via Shopee tool — need separate outreach strategy.

---

## Summary Scorecard

| Metric | Value | Source |
|--------|-------|--------|
| Total MASKED_REPEAT | 433 | mart_customer_tier |
| Zone 1 (active ≤90d) | 69 | query |
| Zone 2 (dormant 91–720d) | 283 | query |
| Zone 3 (lost >720d) | 81 | query |
| Marketplace reachable (Zone 1+2) | **321** | query |
| Zone 2 marketplace (Hug primary target) | **259** | query |
| Median inter-purchase gap (masked-repeat) | **7 days** | fact_orders gap analysis |
| AOV bucket C (1M–2M) safe for 50k voucher | 172 customers (40%) | aov query |
| Bucket A (<500k, negative margin) | 97 customers (22%) | aov query |
| Forward annual CM (base case: 20% R, 5 orders) | **~14M VND** | formula |
| Forward annual CM (optimistic: 30% R, 6 orders) | **~26M VND** | formula |

---

## Unresolved Questions

1. **What is the 683M in the plan?** Is it: (a) Zone 2 marketplace lifetime CM (417M doesn't match), (b) a forward projection with a specific R assumption, or (c) all marketplace CM regardless of zone? Leadership must clarify to align plan numbers with this analysis.

2. **Reactivation rate assumption [R]:** No prior reactivation campaign data exists. The 10–30% range is industry-typical but unverified for this customer base. Leadership must choose a credible R% to anchor the forward opportunity.

3. **CHANNEL_OTHER / CHANNEL_SOCIAL outliers:** Three customers (381f3f…, one social) have combined −1.37B CM. These appear to be data quality issues (zero lifetime_value but large negative CM, or very high-return B2B-type accounts). Should these be excluded from all future segment metrics? Affects lifetime CM reporting materially.

4. **Bucket A exclusion decision:** 97 masked-repeat customers have AOV <500k and negative CM/order on average. Should they be excluded from Hug targeting entirely? If yes, addressable zone 2 drops by ~57 customers (estimate).

5. **Direct-channel masked-repeat (52 customers, 2.18B CM):** These are the highest-value masked customers but Shopee Chat Broadcast doesn't reach them. What is the recontact strategy for this cohort?

---

## Appendix: All Queries Run

All queries executed read-only against `/app/var/data_lake/serving/olap.duckdb` via `docker compose exec -T crm python -c "import duckdb; c=duckdb.connect(..., read_only=True); ..."` from `D:\Vantt\app\data-integration`.

1. Schema inspection: `PRAGMA table_info(main_marts.mart_customer_tier)`, `PRAGMA table_info(main_marts.fact_orders)`
2. 3-zone reachability split with CM aggregates
3. 5-zone sub-band breakdown with positive/negative margin counts
4. Single outlier identification (`customer_key = 381f3f...`, −1.1B CM)
5. Zone breakdown excluding outlier
6. Channel preference (all masked-repeat)
7. Channel preference (zone 2 dormant only)
8. Marketplace-only zone split
9. AOV bucket distribution with 50k voucher % and margin < 50k count
10. Inter-purchase gap analysis (masked-repeat): LAG(ordered_at), DATEDIFF('day', ...)
11. Inter-purchase gap analysis (real-repeat benchmark)
12. Annual order rate via tenure (first→last order, annualized)
13. CM per order by zone (pool-weighted)
14. Marketplace CM per order by zone (forward opportunity denominator)
15. Base number confirmation query

---

**Status:** DONE  
**Summary:** Full 6-part analysis of masked-repeat economics and reachability. Zone 2 marketplace (259 customers) is the primary Hug A2 target. Forward annual opportunity is 14–26M VND (base to optimistic), not 683M — the 683M is a lifetime figure or uses a different definition. Median reorder gap of 7 days confirms Zone 1 is immediately capturable. 50k voucher is safe for AOV ≥1M; Bucket A (<500k) should be excluded due to negative order-level margin.  
**Evidence:** 15 queries ran against olap.duckdb. Key figures: 321 marketplace reachable, 7-day median gap, Zone 2 marketplace 259 customers / 417M lifetime CM / 545k CM/order, 97 Bucket-A customers to exclude, 2 extreme negative outliers (CHANNEL_OTHER/SOCIAL) confirmed.  
**Concerns:** Small N (259 zone-2 marketplace) makes holdout underpowered for statistical significance — Phase 2 holdout will be directional only. Three CHANNEL_OTHER/SOCIAL outlier customers distort aggregate CM by −1.37B; their inclusion/exclusion materially changes headline figures.

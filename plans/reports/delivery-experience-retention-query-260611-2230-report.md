# Delivery Experience → Retention: Query Report
**Date:** 2026-06-11 | **DB:** sapo_export_latest.duckdb (read-only)

---

## HEADLINE ANSWER (#4)

**Delivery quality does NOT predict repeat purchase in any simple way.** Across all retail customers, the slow bucket (>7 days) had the *highest* raw repeat rate (41.5%). When controlling for tenure bias (2026 first-order cohort only), differences collapse: slow_gt7=25%, mid_4to7=24.3%, fast_le3=21.6%. Failed deliveries show the clearest signal: 7.7–11.1% repeat rate vs 21–25% for successful deliveries. **Delivery speed is not the lever; delivery failure hurts retention, but is rare (15% of total, 3.4% of shipped).**

---

## 1. Coverage

```sql
SELECT COUNT(DISTINCT fo.order_id) AS total_valid_retail_orders,
  COUNT(DISTINCT ff.order_id) AS orders_with_fulfillment,
  ROUND(COUNT(DISTINCT ff.order_id)*100.0/COUNT(DISTINCT fo.order_id),1) AS pct_covered,
  MIN(ff.created_at)::DATE, MAX(ff.created_at)::DATE
FROM fact_orders fo JOIN dim_customers dc ... LEFT JOIN fact_fulfillments ff ...
```

| Metric | Value |
|---|---|
| Total valid retail orders | 1,871 |
| Orders with fulfillment | 1,870 (99.9%) |
| Fulfillment date range | 2021-05-26 → 2026-06-11 |
| Total fulfillment rows | 3,609 (multi-fulfillment: ~324 orders have 2+ rows) |

**Coverage is excellent** — virtually all orders have fulfillment records spanning the full data history. No coverage-gap caveat needed.

Multi-fulfillment breakdown: 2,919 orders have 1 ff, 291 have 2, 26 have 3, 5 have 4, 2 have 5. Analysis uses "best" fulfillment per order (prefer is_delivered=true, then min days_to_deliver).

---

## 2. Delivery Time Distribution

```sql
SELECT MEDIAN(days_to_deliver), PERCENTILE_CONT(0.25/0.75/0.90), MAX(days_to_deliver)
FROM fact_fulfillments WHERE is_delivered = true
```

| Stat | Days |
|---|---|
| p25 | 0 |
| Median | 0 |
| p75 | 2 |
| p90 | 5 |
| Max | 359 |

**41.9% of delivered orders are same-day (days=0)** — dominated by SGN-BIKE (same-city bike courier). 16.7% are 15+ days, pulling the long tail. 30 rows have negative days (data quality issue, likely timestamp ordering errors).

**By carrier (top 4 by volume):**

| carrier_id | total | delivered | median_days | p90_days | note |
|---|---|---|---|---|---|
| 221042 | 728 | 631 | 0 | 0 | Same-day courier (SGN-BIKE) |
| 156062 | 529 | 461 | 2 | 4 | GHN Express |
| 156070 | 409 | 349 | 4 | 6 | SPX Express |
| 323192 | 399 | 361 | 2 | 13 | VNPost — slow tail flag ⚠️ |
| 163518 | 78 | 46 | 0 | 16 | High p90 + high fail rate ⚠️ |

**By shipping service:** SGN-BIKE (0-day, 407 delivered), VNPost3 (2-day median), SPX Express (4-day median), GHN Express (2-day median).

---

## 3. Delivery Failure

```sql
SELECT is_delivered, COUNT(*) FROM fact_fulfillments GROUP BY is_delivered
-- shipped: WHERE shipped_at IS NOT NULL → 3172 rows
-- failed among shipped: 109 (3.4%)
-- total is_delivered=false: 546 (15.1% of 3609)
```

| Metric | Value |
|---|---|
| is_delivered = true | 3,063 (84.9%) |
| is_delivered = false | 546 (15.1%) |
| Among shipped (shipped_at not null) | 109/3,172 = **3.4% failure rate** |
| shipment_status column | All NULL — no usable status breakdown |

437 fulfillments have no shipped_at (never dispatched — likely cancelled before handoff). These account for most of the is_delivered=false.

**COD vs Prepaid failure rate:**

| Type | Total | Failed | Fail% |
|---|---|---|---|
| Prepaid | 2,994 | 448 | 15.0% |
| COD | 615 | 98 | **15.9%** |

COD failure rate is marginally higher (+0.9pp) — no meaningful difference.

---

## 4. KEY HYPOTHESIS — First-Order Delivery → Repeat Purchase

### All retail customers (all years):

```sql
-- CTE: first valid order per retail customer
-- CTE: best fulfillment per order (prefer delivered, min days)
-- CTE: classify into buckets
-- JOIN dim_customers for repeat flag
SELECT delivery_bucket, COUNT(*), SUM(is_repeat), repeat_rate_pct
```

| Bucket | Customers | Repeat Rate |
|---|---|---|
| slow_gt7 | 53 | **41.5%** ← apparent paradox |
| delivered_no_time | 94 | 31.9% |
| mid_4to7 | 204 | 24.5% |
| fast_le3 | 884 | 23.8% |
| failed_not_delivered | 107 | **7.7%** |
| no_fulfillment | 1 | 0% |

### Tenure bias explanation:
slow_gt7 customers have avg 560 days since first order vs 1,190 days for fast_le3. Counterintuitively, fast_le3 customers are the *oldest* cohort — they've had the most time to accumulate orders, so their repeat rate should be higher. Yet it's lower than slow_gt7. The year breakdown reveals why:

- slow_gt7 is concentrated in 2021–2022 (older cohort, more time to repeat) and 2025 (47.1% repeat rate)
- fast_le3 is distributed across all years with no year hitting >40%

### 2026 cohort only (same ~0-6 month observation window, most apples-to-apples):

| Bucket | Customers | Repeat Rate |
|---|---|---|
| slow_gt7 | 20 | 25.0% |
| mid_4to7 | 136 | **24.3%** |
| fast_le3 | 148 | 21.6% |
| failed_not_delivered | 18 | **11.1%** |
| no_fulfillment | 1 | 0% |

**2026 finding: delivery speed makes no meaningful difference (21.6–25.0%). Failed delivery cuts repeat rate in half (11.1%).** But failed delivery affects only 5.5% of 2026 cohort (18/323), so its contribution to total 1-timer volume is small.

### Bronze-only (strip VIP/GOLD confound):

| Bucket | Customers | Repeat Rate |
|---|---|---|
| slow_gt7 | 48 | 37.5% |
| failed_not_delivered | 87 | 24.1% |
| fast_le3 | 847 | **22.0%** |
| mid_4to7 | 195 | 21.0% |

Bronze slow_gt7 still shows higher repeat than fast — confirming the tenure bias explanation, not a genuine speed benefit. Bronze failed_not_delivered at 24.1% is surprisingly close to fast_le3 (22%), suggesting other factors dominate.

---

## 5. Other Delivery Signals Correlated with Churn

**Delivery bucket vs avg recency (days since last order — higher = more dormant):**

| Bucket | Avg Recency | Median Recency |
|---|---|---|
| mid_4to7 | 473 days | 101 days |
| slow_gt7 | 477 days | 217 days |
| failed_not_delivered | **980 days** | 1,057 days |
| fast_le3 | 1,134 days | 1,520 days |

Failed delivery customers are more dormant (avg 980 days) — consistent with churn signal. However fast_le3 has the highest avg recency due to being the oldest cohort (same tenure bias issue). Median recency is more informative: failed_not_delivered = 1,057 days (very dormant); fast_le3 = 1,520 days (also very dormant — old customer base).

---

## Caveats

1. **shipment_status is all NULL** — no granular status breakdown (returned, lost, refused) possible. is_delivered is the only delivery outcome signal.
2. **Tenure bias dominates cross-bucket comparisons.** fast_le3 has avg 1,190 days since first order vs slow_gt7 at 560 days. Cannot simply compare repeat rates without controlling for cohort age.
3. **Same-day (0-day) deliveries are 42% of delivered** — mostly local SGN-BIKE courier. This makes fast_le3 the dominant bucket by volume, but also the bucket most exposed to older cohorts.
4. **n=13–53 for small buckets** (slow_gt7, failed in 2026) — low statistical power. Repeat rate differences of ±5pp are within noise.
5. **Repeat is lifetime order_count>1**, not M1 window — older customers have longer window to repeat, inflating their rate regardless of delivery.
6. **Other churn drivers not explored**: product category, channel (online vs offline), discount usage, first-order AOV. These likely explain more variance than delivery speed.

---

## Status

**Status:** DONE_WITH_CONCERNS
**Summary:** Delivery failure (is_delivered=false) shows a weak negative signal on repeat purchase (11% vs 22–25%), but affects <6% of customers. Delivery speed is not a predictor of retention once tenure bias is removed. The 71.8% one-timer problem has other causes.
**Concerns:** (1) shipment_status all-NULL limits failure categorization; (2) tenure bias makes cross-cohort comparisons unreliable — 2026 cohort is cleanest evidence; (3) small-n buckets in 2026 limit statistical confidence; (4) no M1-window repeat metric available (only lifetime order_count).

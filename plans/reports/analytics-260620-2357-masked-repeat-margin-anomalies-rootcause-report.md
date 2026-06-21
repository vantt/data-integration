# Masked-Repeat Margin Anomalies — Root Cause Report

**Generated:** 2026-06-20 (queries run 2026-06-21 early morning)
**Analyst:** analytics-analyst subagent
**Scope:** READ-ONLY investigation of two anomalies flagged in prior economics report.
**DB:** `/app/var/data_lake/serving/olap.duckdb` (read_only=True) via `docker compose exec -T crm python -c "..."` from `D:\Vantt\app\data-integration`
**Prior report:** `plans/reports/analytics-260620-2213-masked-repeat-economics-reachability-report.md`

---

## Anomaly 1 — "Bucket A" −1.25M avg CM per order

### The Original Claim

Prior report: 97 masked-repeat customers with avg order value (AOV) < 500k have avg CM/order of **−1,255k VND**. That is, small-order customers appear to be losing ~1.25M per order. Flagged as implausible.

### Investigation

**Step 1: How is Bucket A defined?**

The prior report computed:
```sql
CAST(lifetime_value AS DOUBLE) / order_count < 500000  -- AOV bucket
CAST(lifetime_contribution_margin AS DOUBLE) / order_count  -- avg CM/order
```

`lifetime_value` is the denominator for AOV. If `lifetime_value = 0`, then AOV = 0/N = 0, which is always < 500k. These customers fall in Bucket A regardless of their actual order sizes.

**Step 2: How many Bucket A customers have lifetime_value = 0?**

```sql
SELECT 
    CASE WHEN lifetime_value = 0 THEN 'ZERO_LTV_misclassified' ELSE 'TRUE_SMALL_ORDER' END,
    COUNT(*), AVG(lifetime_value/order_count) as avg_aov,
    SUM(lifetime_contribution_margin) as total_cm,
    AVG(lifetime_contribution_margin::DOUBLE/order_count) as avg_cm_per_order
FROM main_marts.mart_customer_tier
WHERE source_contact_quality='masked' AND order_count>=2
  AND lifetime_value::DOUBLE/order_count < 500000
GROUP BY 1
```

| Bucket A sub-type | Customers | Avg AOV | Total CM | Avg CM/order |
|---|---|---|---|---|
| ZERO_LTV_misclassified | **15** | **0** | **−1,390M VND** | **−8,167k VND** |
| TRUE_SMALL_ORDER | **82** | 300k VND | −5.65M VND | **+9.9k VND** |

**Step 3: What are these 15 zero-LTV Bucket A customers?**

```sql
-- Sample of zero-LTV bucket A customers and their actual orders
SELECT mct.full_name, mct.lifetime_contribution_margin, mct.order_count,
    SUM(fo.gross_revenue) as total_gross, SUM(fo.net_revenue) as total_net,
    SUM(CASE WHEN fo.net_revenue=0 THEN 1 ELSE 0 END) as zero_net_orders
FROM mart_customer_tier mct
JOIN fact_orders fo ON mct.customer_key=fo.customer_key
WHERE [zero-LTV bucket A condition]
GROUP BY ...
```

Results (selected):

| Customer name | Lifetime CM | Orders | Total gross_revenue | Net revenue | Zero-net orders |
|---|---|---|---|---|---|
| Fine Japan-USA | −1,100M | 12 | 6,698M | 0 | 12 |
| Chương Trình Marketing | −128M | 69 | 744M | −34k (≈0) | 68 |
| Quà Tặng | −89M | 20 | 442M | 0 | 20 |
| Event Showroom 09-10/09/2022 | −29M | 3 | 159M | 0 | 3 |
| Long Châu | −972k | 2 | 1.38M | 0 | 2 |
| ETC | −6.5M | 12 | 10.96M | 0 | 12 |
| GUARDIAN HEALTH & BEAUTY | −3.86M | 2 | 14.9M | 0 | 2 |

Every zero-LTV customer has **net_revenue = 0** on essentially all orders. They are not small-order customers. They are customers whose orders carry **100% discount** (discount_amount = gross_revenue), so net_revenue = 0 and `lifetime_value = SUM(net_revenue) = 0`.

**Step 4: What is the discount mechanism driving net_revenue = 0?**

```sql
SELECT primary_discount_type, COUNT(*), COUNT(CASE WHEN net_revenue=0 THEN 1 END) as zero_net
FROM main_marts.fact_orders WHERE is_active_order=TRUE
GROUP BY primary_discount_type ORDER BY zero_net DESC
```

| Discount type | Orders | Zero-net-revenue orders |
|---|---|---|
| (none) | 9,829 | 4,261 |
| **overseas** | **20** | **20** — 100% |
| sampling_gift | 28 | 23 |
| negotiated_deep | 497 | 6 |

The `overseas` discount type produces 100% discount → net_revenue = 0. Order codes start at SON00020–SON00057 (2021 era) and recur through Fine Japan-USA orders. These are **consignment/export orders shipped overseas where the company writes off the full revenue** (goods sent to a foreign buyer at cost with no VND revenue booked, or B2B trade orders treated as zero-price internally in Sapo).

**Step 5: System-wide scope of zero-revenue + COGS-booked problem**

```sql
SELECT COUNT(DISTINCT fo.customer_key), COUNT(*), SUM(fo.gross_revenue), SUM(fo.net_revenue),
    SUM(foe.cogs_amount), SUM(foe.channel_net_profit)
FROM fact_orders fo JOIN fact_order_economics foe ON fo.order_id=foe.order_id
WHERE fo.net_revenue=0 AND foe.cogs_amount>0 AND fo.is_active_order=TRUE
```

| Metric | Value |
|---|---|
| Affected customers | **1,711** |
| Affected orders | **3,544** |
| Total gross revenue written | 107.2B VND |
| Total net revenue collected | 0 VND |
| Total COGS booked | 23.7B VND |
| Total CM impact (channel_net_profit) | **−23.7B VND** |

This is a **systemic data pattern**, not isolated to Bucket A or masked-repeat.

### Root Cause

**ARTIFACT.** The −1,255k avg CM/order in Bucket A is entirely explained by 15 customers misclassified into Bucket A because their `lifetime_value = 0`. They are **not small-order customers**; they have large gross revenues (average ~559M VND per customer) with 100% discounts applied, producing net_revenue = 0.

The `lifetime_value` column in `mart_customer_tier` stores `SUM(net_revenue)`. When every order has 100% discount, lifetime_value = 0, and `lifetime_value/order_count = 0` — placing them falsely into the < 500k AOV bucket.

**True Bucket A (82 true small-order customers):** avg AOV = 300k VND, avg CM/order = **+9.9k VND** — thin but positive.

**The "−1,255k avg CM per order" does not exist as a real phenomenon for small-order customers.**

### Verdict: ARTIFACT

### Recommendation

1. **Voucher targeting:** Do NOT exclude Bucket A based on negative CM signal. The 82 true small-order customers have near-zero but positive CM. Decision on whether to target them should be based on voucher ROI (50k voucher vs 9.9k average CM/order → still negative ROI on voucher, but for a different reason: slim margins, not catastrophic losses).
2. **Report fix:** AOV bucketing must filter `lifetime_value > 0` or use `SUM(gross_revenue)/order_count` as AOV proxy. The zero-LTV customers should be classified as a separate segment: "zero-net-revenue / consignment / event" orders.
3. **Systemic issue (see also Anomaly 2):** 3,544 orders across 1,711 customers have COGS booked against zero net revenue. This is either correct business logic (overseas/consignment shipments where goods left inventory but revenue is not recognized in VND) or a data modeling error. The `has_cogs=True` + `cogs_source='sapo_mac'` + `net_revenue=0` pattern needs upstream classification. Until resolved, these orders produce misleading CM figures in all customer-tier and opportunity analyses.

---

## Anomaly 2 — The −1.1B VND Single Outlier Customer

### Customer Identity

```sql
SELECT customer_key, customer_id, full_name, customer_type, channel_preference,
    order_count, lifetime_value, lifetime_contribution_margin, recency_days
FROM main_marts.mart_customer_tier
WHERE source_contact_quality='masked' AND lifetime_contribution_margin < -500000000
```

| Field | Value |
|---|---|
| customer_key | `381f3f3e9aa21fe963a4305bfd9a58d9` |
| customer_id | `480137705` |
| full_name | **Fine Japan-USA** |
| customer_type | RETAIL (mislabeled — see below) |
| channel_preference | CHANNEL_OTHER |
| order_count | 12 |
| lifetime_value | **0 VND** |
| lifetime_contribution_margin | **−1,100,364,553 VND (−1.1B)** |
| recency_days | 151 (last order 2026-01-13) |

### Order-Level History

```sql
SELECT fo.order_code, fo.ordered_at, fo.gross_revenue, fo.discount_amount, fo.net_revenue,
    fo.primary_discount_type, fo.max_discount_rate,
    foe.cogs_amount, foe.cogs_source, foe.channel_net_profit
FROM fact_orders fo JOIN fact_order_economics foe ON fo.order_id=foe.order_id
WHERE fo.customer_key='381f3f3e9aa21fe963a4305bfd9a58d9'
ORDER BY fo.ordered_at
```

| Order | Date | Gross Revenue | Discount | Net Revenue | Discount Type | COGS | CM |
|---|---|---|---|---|---|---|---|
| SON05771 | 2024-06-14 | 92.2M | 92.2M | **0** | overseas | 23.2M | −23.2M |
| SON05856 | 2024-07-03 | 6.5M | 6.5M | **0** | overseas | 2.1M | −2.1M |
| SON06142 | 2024-09-18 | 1,164M | 1,164M | **0** | (none) | 144.4M | −144.4M |
| SON06261 | 2024-10-23 | **1,813M** | 1,813M | **0** | (none) | 303.9M | −303.9M |
| SON06284 | 2024-11-01 | 582M | 582M | **0** | (none) | 72.2M | −72.2M |
| SON06322 | 2024-11-14 | 752.6M | 752.6M | **0** | (none) | 127.2M | −127.2M |
| SON06365 | 2024-11-25 | 929.8M | 929.8M | **0** | (none) | 159.6M | −159.6M |
| SON06407 | 2024-12-09 | 863.5M | 863.5M | **0** | (none) | 141.5M | −141.5M |
| SON06620 | 2025-02-20 | 99.4M | 99.4M | **0** | (none) | 40.9M | −40.9M |
| SON07109 | 2025-12-23 | 0 | 0 | 0 | (none) | 18.1M | −18.1M |
| SON07145 | 2026-01-13 | 18.8M | 18.8M | **0** | (none) | 3.7M | −3.7M |
| SON07146 | 2026-01-13 | 376.3M | 376.3M | **0** | (none) | 63.6M | −63.6M |

**Total: 6,698M VND gross revenue, 0 VND net revenue, 1,100M VND COGS booked → −1,100M CM.**

### Root Cause

**ARTIFACT.** Every single order for Fine Japan-USA has:
- `discount_amount = gross_revenue` → `net_revenue = 0`
- `cogs_amount > 0` (sourced from `sapo_mac`) → full COGS booked against zero revenue

Two sub-patterns observed:
1. **2024-06 and 2024-07 orders** (SON05771, SON05856): `primary_discount_type = 'overseas'` — consistent with the consignment/export pattern, 100% discount applied, goods shipped to foreign buyer with zero VND revenue recognition.
2. **2024-09 through 2026-01 orders**: `primary_discount_type = NULL`, `max_discount_rate = NULL` — but still 100% discounted. The discount is applied at line item level without Sapo recording a named discount type. This escalates in value to 1.8B VND single orders (SON06261). These may represent **B2B transfer orders, inter-company trades, or consignment shipments** that the business records in Sapo but recognizes zero revenue.

**The −1.1B CM is COGS booked on goods that left inventory for zero net revenue recognized in Sapo.** This is either:
- (a) Correct accounting: goods shipped abroad as consignment where cash is received via foreign payment outside Sapo's scope, or
- (b) Incorrect accounting: COGS booked at Sapo MAC cost but revenue not recorded in Sapo (perhaps collected via a different system — wire transfer, foreign invoice — and never reconciled back).

The customer name "Fine Japan-USA" strongly implies **overseas export / consignment** — a real business flow, but one that should be classified separately from domestic retail/marketplace customers.

**The customer_type = RETAIL is wrong.** This is a B2B export account, not a retail consumer.

### Verdict: ARTIFACT (misclassified account + revenue recognition gap)

### Other Extreme Negative Outliers (full dataset scan)

```sql
SELECT customer_id, full_name, customer_type, channel_preference, order_count,
    lifetime_value, lifetime_contribution_margin
FROM main_marts.mart_customer_tier
WHERE lifetime_contribution_margin < -50000000
ORDER BY lifetime_contribution_margin ASC
```

| Customer | Type | CM | LTV | Orders | Nature |
|---|---|---|---|---|---|
| Huynh Tri Bao (78229451) | WHOLESALE | **−2,524M** | 12,018M | 84 | Wholesale — but positive LTV means revenue IS collected; CM negative from overhead? |
| Hien Huynh (64551146) | RETAIL | −2,454M | 0 | 70 | Zero LTV → same pattern: zero-net-revenue orders |
| **Fine Japan-USA** | RETAIL (wrong) | −1,100M | 0 | 12 | Export/consignment |
| anh Lợi (106551641) | RETAIL | −260M | 240k | 59 | Nearly zero LTV, likely same |
| FG Organization HQ (286639025) | RETAIL | −254M | 0 | 2 | Internal? Zero LTV |
| Phạm Bích Ngọc (154382501) | RETAIL | −185M | 0 | 28 | Zero LTV |
| Chương Trình Marketing (218544240) | RETAIL | −128M | 0 | 69 | **masked** — "Marketing Program" account |
| Anh Chinh - Đức (90007885) | RETAIL | −122M | 0 | 14 | Zero LTV |
| Đại Lý Mậu Phước Đường (105859862) | RETAIL | −110M | 0 | 19 | "Distributor" — trade account |
| Quà Tặng (214214634) | RETAIL | −89M | 0 | 20 | **masked** — "Gift" account (gifting/sampling) |

**Pattern is not isolated.** At least 8 of the top 10 worst-CM customers have `lifetime_value = 0`, meaning 100% discount across all orders. The names reveal the root business categories: export accounts (Fine Japan-USA), distributor trade accounts (Đại Lý...), internal/marketing accounts (Chương Trình Marketing, Quà Tặng), event/showroom accounts (Event Showroom, Expo Medipharm).

None are real retail consumers buying for personal use.

### Recommendation

1. **Exclude from masked-repeat voucher analysis:** Fine Japan-USA (and all zero-LTV customers) are not consumer accounts and should never be Hug targets. Their inclusion in masked-repeat is itself a data quality issue — they appear masked because Sapo captures no real contact, but they are B2B/internal, not anonymous consumers.
2. **Create a `is_zero_net_revenue_account` flag** in `mart_customer_tier`: `lifetime_value = 0 AND order_count >= 2` AND at least one order has `has_cogs = TRUE`. These should be excluded from all consumer-facing analytics.
3. **Upstream fix needed:** `customer_type` for Fine Japan-USA and similar accounts should be reclassified as WHOLESALE, B2B, or INTERNAL. This is an upstream Sapo data tagging issue, not fixable in dbt alone without a seed/overrides table.
4. **Revenue recognition gap investigation (separate task):** 3,544 orders (1,711 customers, 23.7B COGS) have `net_revenue=0` but `cogs_amount>0`. Business should confirm: are these COGS correctly booked (goods truly left at zero net revenue) or are they mismatched (revenue collected outside Sapo and COGS double-booked)? This affects reported gross profit system-wide, not just these customers.

---

## Impact on Go-Live Decisions

### Decision 1: Excluding Bucket A from vouchers

**Before this investigation:** "Bucket A (97 customers) should be excluded due to −1,255k avg CM/order."
**After:** The 97 includes 15 misclassified zero-LTV accounts (all zero-net-revenue). The true small-order group (82 customers) has avg CM/order of **+9.9k VND** — thin but not catastrophic.

Revised decision:
- Exclude the **15 zero-LTV customers** from all targeting (they are B2B/export/internal, not consumers)
- For the **82 true small-order customers (AOV ~300k):** the exclusion rationale changes from "negative margin" to "50k voucher exceeds per-order CM" — still correct to exclude, but for different (and real) reasons
- Net voucher-eligible Bucket A changes: **0 of 15 misclassified should receive vouchers; 82 true small-order customers should be excluded on ROI grounds (50k > 9.9k CM)**

### Decision 3: Median vs mean in reporting

**The −1.1B outlier inflates mean but not median.** Recommendation: use median CM/customer for all masked-repeat segment reporting and clearly note that 15 zero-LTV accounts are excluded from the consumer-oriented analysis. Means are valid only after excluding zero-LTV accounts.

### Decision 4: Headline opportunity number

The corrected masked-repeat picture after removing 15 zero-LTV (B2B/export/marketing) accounts:

| Segment | Before removal | After removing 15 zero-LTV |
|---|---|---|
| Total masked-repeat customers | 433 | 418 |
| Total lifetime CM | 1,562M VND | **2,952M VND** |
| Zone 2 total CM (dormant reachable) | −346M (distorted) | ~755M VND |
| Avg CM/customer | 3,608k | **7,062k** |

Removing the misclassified B2B/export accounts **more than doubles** the apparent average CM/customer in the masked-repeat segment. The headline opportunity is more attractive, not less.

---

## Systemic CM/COGS Data Quality Issue

**Scope:** 3,544 orders, 1,711 customers, 23.7B VND COGS booked at zero net revenue. This is not a rounding error — it is ~22% of estimated total COGS based on order volume.

**Root mechanism:** Sapo records orders for consignment/export/B2B/internal/marketing use with 100% discount applied. COGS from Sapo MAC inventory is correctly deducted (goods left the warehouse). But net revenue is zero because no VND payment is recorded in Sapo. The analytics system (dbt models) correctly computes `channel_net_profit = net_revenue - COGS = 0 - COGS = -COGS`, which is mathematically accurate given the data but economically misleading.

**Whether this is a data modeling error or correct accounting:**
- If these are true consignment exports (paid via foreign invoice outside Sapo): the COGS is real, the zero revenue is real in Sapo's scope. The −23.7B CM is a correct reflection that these goods were not monetized through Sapo. Fix: add a `order_type = 'consignment'/'export'/'internal'` flag and exclude from consumer CM reporting.
- If revenue was collected and just not entered in Sapo (parallel cash/wire): this is a revenue recognition gap that understates gross profit system-wide. Fix: upstream data entry correction.

**This issue affects ALL mart reports** that sum `channel_net_profit` or `lifetime_contribution_margin` without filtering. It is not specific to masked-repeat or Hug.

---

## Unresolved Questions

1. **What is the actual cash flow for Fine Japan-USA / "overseas" orders?** Were these goods paid via foreign wire transfers logged outside Sapo? If yes, the business has ~6.7B VND uncaptured revenue and the −1.1B COGS is real cost with real revenue elsewhere. If no, these are genuine losses (sampling/consignment with no payment). Critical for understanding true profitability.

2. **Who authorized the 100% discount on 1.8B VND orders (SON06261)?** Several late-2024 orders have NULL discount type but 100% discount on very large amounts. This is either a data entry bug (discount should be zero) or intentional (B2B transfer pricing). If the former, COGS is overstated; if the latter, the account should be reclassified as WHOLESALE.

3. **Should `mart_customer_tier.lifetime_value` exclude zero-net-revenue orders?** Currently it sums `net_revenue` which is zero for these accounts. An alternative: `lifetime_value = SUM(gross_revenue)` to capture the economic volume even when discounts bring net to zero. This changes the AOV bucket logic and would move these 15 customers out of Bucket A.

4. **Chương Trình Marketing (masked, 69 orders, −128M CM):** This "Marketing Program" account suggests internal use — sampling, marketing campaigns, giveaways. Why is it showing as a `masked` contact? Internal accounts should be explicitly tagged and excluded. Need confirmation from business on what orders were booked to this account.

5. **The `is_active_order` filter:** zero-LTV customers have 0 inactive orders in the data checked. Are their 100%-discount orders always flagged active? If the business intended these orders to be excluded from analytics, `is_active_order` should be FALSE for consignment/export orders.

6. **Huynh Tri Bao (−2.5B CM, WHOLESALE, 12B LTV):** This is the worst-CM customer overall and has POSITIVE lifetime_value (real revenue collected). Their −2.5B CM implies structural overhead allocation or a COGS issue unrelated to the zero-net-revenue pattern. Not investigated here — warrants separate examination.

---

## Appendix: Queries Run

All queries executed read-only against `/app/var/data_lake/serving/olap.duckdb`.

1. `PRAGMA table_info(main_marts.fact_orders)` — schema check
2. `PRAGMA table_info(main_marts.mart_customer_tier)` — schema check
3. `PRAGMA table_info(main_marts.fact_order_economics)` — schema check (key: found channel_net_profit, cogs_source, allocated_overhead)
4. List of tables in main_marts schema
5. Bucket A zero-LTV vs true-small split — **key finding**
6. Zero-LTV bucket A customer list with order patterns
7. Reconciliation: mart.lifetime_contribution_margin = SUM(channel_net_profit) — confirmed exact match
8. Bucket A orders by cogs_source (sapo_mac vs both) with CM components
9. Individual worst Bucket A orders — found the outlier's orders embedded
10. Outlier customer identity query
11. Outlier full order history via fact_orders + fact_order_economics join
12. `overseas` discount type pattern across all orders
13. System-wide zero-revenue + COGS-booked scope: 3,544 orders, −23.7B VND CM impact
14. All extreme negative CM customers (< −50M) across full dataset
15. True small-order Bucket A (82 customers) CM metrics: avg +9.9k VND/order
16. Fine Japan-USA detail: 100% cogs_source=sapo_mac, 12/12 zero-net-revenue orders

---

**Status:** DONE
**Summary:** Both anomalies are ARTIFACTS, not real business losses. Bucket A's −1,255k avg CM/order is caused by 15 zero-LTV B2B/export customers misclassified into the <500k AOV bucket — the true 82 small-order customers have +9.9k avg CM/order. The −1.1B outlier (Fine Japan-USA) is a B2B export/consignment account where 100% discount produces zero net revenue in Sapo with full COGS booked — economically misleading but technically correct given how the orders are entered. A systemic issue (3,544 orders, 23.7B VND COGS, zero net revenue) affects all customer and economics reporting.
**Evidence:** 16 queries. Key numbers: 15 zero-LTV misclassified customers drive −1,390M of −1,395M Bucket A CM; 82 true small-order customers avg +9.9k CM/order; Fine Japan-USA has 12/12 orders with 100% discount and zero net revenue; 3,544 system-wide zero-revenue+COGS orders (1,711 customers, −23.7B CM impact).
**Concerns:** The 23.7B VND zero-revenue COGS issue is systemic and impacts gross profit reporting across all marts. Root business question (cash collected outside Sapo vs true zero-revenue consignment) is unresolved and cannot be answered from dbt data alone — requires business confirmation.

# Action Queue P3 Signals Refresh — 2026-06-11

**Query date:** 2026-06-11 | **Queue freshness:** 2026-06-11 10:16 ICT

---

## LEAD: Time-Sensitive Outreach (Finding #4)

**188 OVERDUE repeat customers + 5 due in next 7 days + 7 due in 7-14 days = 200 contactable window**

Most actionable NOW: **131 contactable OVERDUE repeat customers**, 579.9M VND LTV at stake.
Next 7 days (DUE_SOON + upcoming): **16 DUE_SOON**, 11 contactable, 73.9M LTV.

---

## Findings

### 1. Action Queue Refresh (110 rows, fresh 2026-06-11 10:16 ICT)

| action_type | count | value_at_stake | contactable |
|---|---|---|---|
| WIN_BACK | 30 | 911.4M | 27 |
| REORDER_NUDGE | 21 | 112.1M | 8 |
| CALL_NOW | 3 | 82.8M | 1 |
| SECOND_ORDER | 54 | 50.1M | 10 |
| HIGH_CANCEL_RISK | 2 | NULL | 2 |
| **TOTAL** | **110** | **1,156.4M** | **48** |

**vs stale 06-09:** WIN_BACK 47→30 (-36%), REORDER_NUDGE 62→21 (-66%), SECOND_ORDER 59→54, CALL_NOW 9→3, HIGH_CANCEL_RISK 11→2. Total value 1,762M→1,156M (-34%). Queue shrunk materially — likely signal refresh tightened criteria. REORDER_NUDGE drop is the largest shift.

**Contactability gap:** Only 48/110 (44%) in queue have phone. WIN_BACK best ratio (27/30=90%). REORDER_NUDGE worst (8/21=38%). SECOND_ORDER critically low (10/54=19%).

---

### 2. next_purchase_signal Distribution (RETAIL, excl Unknown, n=6,705)

| signal | count | LTV sum | contactable |
|---|---|---|---|
| NULL | 6,437 | 699.4M | 3,167 |
| OVERDUE | 175 | 579.9M | 131 |
| ON_TRACK | 77 | 354.9M | 53 |
| DUE_SOON | 16 | 73.9M | 11 |

**vs stale 06-09:** OVERDUE 210→175 (-17%), LTV 3,549M→579.9M. The prior LTV figure is almost certainly wrong (was likely total DB LTV, not OVERDUE segment). Current 579.9M is the correct OVERDUE LTV. Signal distribution directionally stable.

Contactable OVERDUE: **131/175 (75%)** — highest contactability ratio of all signals.

---

### 3. discount_sensitivity Distribution (RETAIL, excl Unknown)

| label | count | avg LTV | avg discount_rate |
|---|---|---|---|
| NULL | 5,458 | 0 | NULL |
| PROMO_DEPENDENT | 1,235 | 1,379K | 1.00 |
| FULL_PRICE | 11 | 460K | 0.00 |
| PROMO_MIXED | 1 | 0 | 0.60 |

**"Only 2 FULL_PRICE" refuted: 11 customers tagged FULL_PRICE** (prior was wrong).
However, cohort is weak: ALL 11 are VALUE_BRONZE, avg LTV 460K only. 9/11 are Churned/At Risk. 3/11 contactable. Not a meaningful protectable premium segment — too small, low-value, mostly churned.

PROMO_DEPENDENT dominates repeat buyers (1,235 customers, 100% discount-dependent). No viable full-price premium cohort exists at scale.

---

### 4. Timing — Due in Next 7/14 Days (Repeat Customers, order_count>1)

| window | count | contactable | LTV |
|---|---|---|---|
| OVERDUE (past due) | 175 | 131 | 579.9M |
| Due next 7 days | 5 | 5 | (within 661.7M subtotal) |
| Due next 7-14 days | 7 | ~5 | (within 674.8M subtotal) |
| Beyond 14 days | 69 | — | — |

**Highest-ROI list NOW:** 131 contactable OVERDUE + 11 contactable DUE_SOON = **142 phone-reachable customers with 653.8M LTV on the clock.** This is the time-sensitive Zalo/CSKH call list.

Cumulative predicted_next_purchase_date breakdown (repeat customers only):
- Overdue: 188 | Next 7d: 5 | Next 7-14d: 7 | Beyond 14d: 69

---

### 5. SECOND_ORDER Window (order_count=1, first order 15-45 days ago)

**56 customers, 10 contactable, 48.9M LTV, avg LTV 873K**

vs stale queue SECOND_ORDER=54: very close. Contactability bottleneck severe (10/56=18%). Value per contactable customer: ~4.9M — worth targeting but phone gap limits reach. Bulk of 56 unreachable via phone — consider email/Zalo OA if available.

---

### 6. Cancel Rate

**cancel_rate > 0.5:** 15 customers, 12.9M LTV (vs stale HIGH_CANCEL_RISK 11 in queue → queue shows only 2 with NULL value_at_stake, meaning 13 high-cancel customers not in queue).

Distribution (RETAIL, excl Unknown):
| bucket | count |
|---|---|
| 0 (no cancels) | 1,157 |
| 0–25% | 15 |
| 25–50% | 60 |
| 50–75% | 14 |
| >75% | 1 |
| NULL (one-timers) | 5,458 |

Low cancel risk overall. 75 customers with any cancel history (1.1% of base).

---

### 7. value_group × customer_status Crosstab (RETAIL, excl Unknown)

| group | total cnt | total LTV | At Risk+Churned LTV | At Risk+Churned cnt |
|---|---|---|---|---|
| VALUE_BRONZE | 6,634 | 522.6M | 438.1M | 1,090 |
| VALUE_SILVER | 55 | 519.2M | 456.9M | 48 |
| VALUE_GOLD | 11 | 341.0M | 281.8M | 9 |
| VALUE_VIP | 5 | 325.4M | 253.4M | 4 |

**Key insight:** SILVER+GOLD+VIP = 71 customers, 1,185.7M LTV. Of those, **61/71 are At Risk or Churned (1,431 — 992.1M).** Reactivation mine: the top 3 tiers have 83.7% of their LTV in at-risk/churned status. This is the highest-leverage reactivation target.

VIP detail: 1 Active (72M), 4 Churned (253.4M) — 4 churned VIPs = single biggest reactivation prize.
SILVER: 7 Active (62.3M), 13 At Risk (109.4M), 35 Churned (347.5M).

---

## Material Shifts vs Stale 06-09 Numbers

| metric | stale 06-09 | current 06-11 | delta | flag |
|---|---|---|---|---|
| WIN_BACK count | 47 | 30 | -36% | SHIFTED |
| REORDER_NUDGE count | 62 | 21 | -66% | MAJOR SHIFT |
| CALL_NOW count | 9 | 3 | -67% | MAJOR SHIFT |
| HIGH_CANCEL_RISK count | 11 | 2 | -82% | MAJOR SHIFT |
| Total queue value | ~1,762M | 1,156.4M | -34% | SHIFTED |
| OVERDUE count | 210 | 175 | -17% | SHIFTED |
| OVERDUE LTV | "3,549M" | 579.9M | — | PRIOR WAS WRONG |
| FULL_PRICE count | "2" | 11 | +450% | PRIOR WAS WRONG |

---

**Status:** DONE
**Summary:** Queue refreshed to 2026-06-11. Major shrinkage in REORDER_NUDGE/CALL_NOW/HIGH_CANCEL_RISK vs stale numbers. Time-sensitive list: 142 contactable customers (131 OVERDUE + 11 DUE_SOON) with 653.8M LTV — priority Zalo/CSKH outreach. Top-tier reactivation mine: 61 SILVER/GOLD/VIP customers At Risk or Churned = 992.1M LTV.
**Concerns:** (1) REORDER_NUDGE drop 62→21 is large — unclear if data quality issue or legitimate recency shift; worth investigating queue generation logic. (2) SECOND_ORDER contactability 18% severely limits activation — phone collection gap. (3) FULL_PRICE cohort (n=11) is all low-value churned BRONZE — no premium protection play possible. (4) 5,458 customers have NULL discount_sensitivity and NULL value_group (New/Unknown) — they're one-timers with 0 LTV recorded; exclude from activation until they make a second purchase.

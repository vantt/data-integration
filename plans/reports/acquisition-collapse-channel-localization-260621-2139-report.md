# Acquisition Collapse — Channel Localization Report
**Generated:** 2026-06-21 | **Analyst:** analytics-analyst  
**Data:** fact_orders + dim_channels parquet (snapshot 20260621) | **Scope:** B2C non-B2B, status=COMPLETED, net_revenue>0

---

## (1) VERDICT

**The collapse is Shopee — a peak-to-trough drop of 73% in new-customer intake, from a Shopee-driven Q3 2024 high straight off a cliff in Q2–Q3 2025. The recovery is incomplete and stalled.**

### Channel-by-channel:

| Channel | Peak New Custs/Qtr | Current (2026-Q2) | Change | Pattern |
|---------|-------------------:|------------------:|--------|---------|
| **Shopee** | **325 (2024-Q3)** | **105** | **–68%** | **CLIFF: 325→61 in 3 qtrs** |
| Selly | 83 (2022-Q2) | 0 | –100% | CLOSED (platform killed) |
| Lazada | 53 (2021-Q4) | 1 | –98% | Slow bleed to near-zero |
| POS-Offline | 38 (2023-Q1) | 0 | –100% | Shut down / no new cust |
| Tiki | 29 (2021-Q2) | 0 | –100% | Exit by 2024 |
| Facebook/Social | 23 (2024-Q2) | 1 | –96% | Near-zero |
| **Zalo** | **13 (2022-Q3)** | **6** | **–54%** | **Recovering slightly** |
| **Web/Direct** | **17 (2024-Q4)** | **4** | **–77%** | **Weak** |

**What grew while others fell:** Nothing truly grew. The 2024-Q2/Q3 recovery was entirely Shopee recovering, then collapsing again. The only relative story is that Zalo and Web/Direct now represent a higher share than at peak, but in absolute terms both are small.

**Gateway-SKU shift: YES.** Acquisition SKU mix shifted materially. 2022 peak was driven by cheap/mass SKUs (UV sunscreen tablets VCSC22003G001, Bone's Calcium for Kids VCSP22001B001 — low unit prices ~300–350K VND) as entry products. By 2025-2026 gateway SKUs reverted to premium core (Cordyceps, Natto Kinase ~700K–2M VND AOV). The 2022 volume spike was partly fueled by a low-priced SKU bringing high-volume Selly/Shopee new buyers. 2026-Q2 shows a new anomaly: Coix Beauty Tablets (VCSC23054B001, ~230K/unit) spiking to #1 gateway SKU for 48 buyers — a potential new Selly-like cheap-entry play but only on Shopee.

**Structural break quarter: 2025-Q2.** Shopee new customers went 325 → 248 → 217 → 106 → 61 (2024-Q3 through 2025-Q3) — a near-linear cliff over 4 quarters. No single quarter snapped; it was a fast multi-quarter bleed starting immediately after 2024-Q3.

---

## (2) THE SIX TIME-SERIES TABLES

### Table 1 — New Customers per Quarter by Channel (B2C only)

> Scope: scope_b2b=false, is_active_order=true, net_revenue>0, status=COMPLETED.  
> Channel = channel of customer's FIRST qualifying order.  
> Excluded: WHOLESALE (Dai Ly, Cho Si), US/Export, Internal/Other (Other, Qua Tang, Uu dai NV, Test).

| Qtr | Shopee | Selly | Lazada | Other-Mkt | POS | Facebook | Zalo | Web/Direct | Tiki | TOTAL B2C |
|-----|-------:|------:|-------:|----------:|----:|---------:|-----:|-----------:|-----:|----------:|
| 2021-Q2 | 15 | 0 | 8 | 0 | 3 | 2 | 1 | 1 | 27 | 57 |
| 2021-Q3 | 9 | 0 | 8 | 0 | 0 | 8 | 7 | 7 | 11 | 50 |
| 2021-Q4 | 64 | 0 | 53 | 0 | 0 | 14 | 7 | 4 | 29 | 171 |
| 2022-Q1 | 180 | 7 | 23 | 0 | 0 | 4 | 2 | 2 | 12 | **228** |
| **2022-Q2** | **208** | **83** | **18** | **2** | **0** | **4** | **0** | **6** | **6** | **327** |
| 2022-Q3 | 192 | 5 | 17 | 4 | 9 | 6 | 7 | 9 | 6 | **255** |
| 2022-Q4 | 86 | 0 | 21 | 10 | 23 | 1 | 1 | 5 | 6 | 153 |
| 2023-Q1 | 119 | 0 | 24 | 5 | 38 | 4 | 12 | 2 | 1 | 205 |
| 2023-Q2 | 120 | 0 | 6 | 4 | 21 | 10 | 13 | 7 | 1 | 182 |
| 2023-Q3 | 136 | 0 | 4 | 3 | 13 | 12 | 12 | 3 | 5 | 188 |
| 2023-Q4 | 85 | 0 | 8 | 3 | 15 | 17 | 8 | 2 | 6 | 144 |
| 2024-Q1 | 130 | 0 | 2 | 2 | 11 | 14 | 12 | 5 | 0 | 176 |
| **2024-Q2** | **274** | **0** | **1** | **2** | **0** | **23** | **14** | **7** | **1** | **322** |
| **2024-Q3** | **325** | **0** | **1** | **1** | **0** | **18** | **10** | **10** | **0** | **365** |
| 2024-Q4 | 246 | 0 | 0 | 2 | 0 | 15 | 3 | 17 | 0 | 283 |
| 2025-Q1 | 217 | 0 | 0 | 2 | 0 | 13 | 5 | 5 | 0 | 242 |
| **2025-Q2** | **106** | **0** | **0** | **4** | **0** | **6** | **2** | **15** | **0** | **133** |
| 2025-Q3 | 61 | 0 | 1 | 2 | 0 | 2 | 8 | 11 | 0 | 85 |
| 2025-Q4 | 96 | 0 | 1 | 2 | 0 | 3 | 7 | 3 | 0 | 112 |
| 2026-Q1 | 96 | 0 | 5 | 0 | 0 | 3 | 6 | 3 | 0 | 113 |
| 2026-Q2 | 105 | 0 | 1 | 1 | 0 | 1 | 6 | 4 | 0 | 118 |

**Key inflection:** 2024-Q3 was the second and final peak (365 B2C new custs); 2025-Q2 was the cliff (-64% quarter-over-quarter). Shopee alone went from 325 → 61 in three quarters.

**Note on discrepancy with prior cohort report:** Prior report's cohort (550 peak in 2022-Q2) was using a broader scope (included US, Internal/Other, WHOLESALE customers). This analysis uses ONLY retail B2C non-B2B channels. The 2022-Q2 "550" cohort included ~220 US-channel + wholesale customers not counted here. The pure B2C retail peak was 327 (2022-Q2) or 365 (2024-Q3).

---

### Table 2 — Total Orders & Net Revenue per Quarter by Channel

| Qtr | Shopee Orders | Shopee Rev (M VND) | Zalo Rev (M) | FB/Social Rev (M) | Web/Direct Rev (M) | Lazada Rev (M) | **B2C Total Rev (M)** |
|-----|:-------------:|-------------------:|:------------:|:-----------------:|:-----------------:|:-------------:|---------------------:|
| 2021-Q4 | 83 | 169 | 57 | 144 | 19 | 118 | 555 |
| 2022-Q1 | 228 | 390 | 72 | 96 | 2 | 69 | 657 |
| 2022-Q2 | 276 | 395 | 17 | 50 | 26 | 64 | 644 |
| 2022-Q3 | 270 | 371 | 104 | 31 | 68 | 48 | 743 |
| 2022-Q4 | 140 | 234 | 12 | 4 | 18 | 55 | 456 |
| 2023-Q1 | 176 | 236 | 61 | 4 | 10 | 49 | 507 |
| 2023-Q2 | 156 | 195 | 160 | 51 | 26 | 14 | 528 |
| 2023-Q3 | 136 | 188 | 153 | 43 | 23 | 25 | 520 |
| 2023-Q4 | 85 | 120 | 144 | 120 | 11 | 52 | 514 |
| 2024-Q1 | 136 | 151 | 145 | 28 | 28 | 1 | 414 |
| 2024-Q2 | 327 | 292 | 139 | 58 | 23 | 6 | 521 |
| 2024-Q3 | 445 | 446 | 51 | 43 | 16 | 10 | 565 |
| 2024-Q4 | 381 | 439 | 100 | 80 | 32 | — | 652 |
| 2025-Q1 | 311 | 346 | 120 | 43 | 24 | — | 536 |
| 2025-Q2 | 165 | 164 | 64 | 32 | 13 | 1 | 278 |
| 2025-Q3 | 111 | 142 | 124 | 11 | 11 | 1 | 290 |
| 2025-Q4 | 150 | 144 | 116 | 61 | 7 | 2 | 334 |
| 2026-Q1 | 180 | 275 | 78 | 14 | 49 | 15 | 430 |
| 2026-Q2 | 199 | 242 | 106 | 6 | 10 | 1 | 368 |

**Revenue vs customer-count story:** Revenue collapsed less severely than new-customer count. 2025-Q2 revenue was 278M vs 521M in 2024-Q2 (–47%) but new customers fell 133 vs 322 (–59%). The gap = AOV rising on Shopee (1,432→995→1,217 K VND), Zalo becoming proportionally more important (Zalo revenue 23% of now-base vs 9% at peak).

---

### Table 3 — Gateway SKU Shift by Acquisition Quarter (Top 3 by New Buyers)

> SKU = product acquired on first-ever order.

| Qtr | #1 Gateway SKU | New Buyers | #2 Gateway SKU | New Buyers | #3 Gateway SKU | New Buyers |
|-----|---------------|:----------:|---------------|:----------:|---------------|:----------:|
| 2021-Q2 | COR1 Cordyceps (old) | 29 | Metabo Green Tea | 21 | Fucoidan | 19 |
| 2022-Q1 | Metabo Green Tea | 53 | Bone's Calcium Kids | 38 | Shark Cartilage | 38 |
| **2022-Q2** | **UV Care+ (sunscreen)** | **79** | **Bone's Calcium Kids** | **58** | **Shark Cartilage** | **56** |
| **2022-Q3** | **Shark Cartilage** | **58** | **UV Care+** | **49** | **Cordyceps** | **40** |
| 2022-Q4 | UV Care+ | 24 | Hyaluron & Collagen | 20 | Shark Cartilage | 20 |
| 2023-Q1 | Cordyceps VT | 50 | UV Care+ | 20 | Fucoidan | 17 |
| 2023-Q3 | Fucoidan | 31 | Hyaluron & Collagen | 25 | Cordyceps | 25 |
| 2024-Q1 | UV Care+ | 52 | Cordyceps | 21 | Hyaluron C-pack | 16 |
| **2024-Q2** | **UV Care+** | **54** | **Shark Cartilage** | **38** | **Hyaluron C-pack** | **25** |
| **2024-Q3** | **Shark Cartilage** | **60** | **Cordyceps** | **31** | **Fujina Cardio** | **27** |
| 2024-Q4 | Cordyceps | 42 | Natto Kinase | 36 | Shark Cartilage | 30 |
| 2025-Q1 | Cordyceps | 31 | Natto Kinase | 27 | Shark Cartilage | 21 |
| **2025-Q2** | **Natto Kinase** | **18** | **Coix Beauty** | **10** | **Gaba Blood** | **9** |
| 2025-Q3 | Cordyceps | 27 | Gaba Blood | 7 | Natto Kinase | 7 |
| **2025-Q4** | **Bone's Calcium Kids** | **41** | **Cordyceps** | **19** | **UV Care+** | **8** |
| **2026-Q1** | **Cordyceps VT** | **29** | **Natto Kinase** | **28** | **Coix Beauty** | **15** |
| **2026-Q2** | **Coix Beauty** | **48** | **Cordyceps VT** | **25** | **Natto Kinase** | **12** |

**Key observations:**
1. **2022-peak gateway:** UV Care+ (sunscreen, ~300K/unit) + Bone's Calcium for Kids (kids supplement, ~200K/unit) — **low-priced, wide-appeal entry SKUs** that pulled in high-volume new buyers via Selly/Shopee promos.
2. **2023–2024 mid-period:** UV Care+ remained gateway, then Shark Cartilage dominated 2024-Q3 peak (60 buyers).
3. **2025-2026 new:** Core functional supplement SKUs (Cordyceps, Natto Kinase) and Coix Beauty Tablets. Coix Beauty at #1 in 2026-Q2 (48 buyers at ~230K/unit) looks like a Shopee promo-driven entry product — could be early signal of a recovery driver.
4. **Bone's Calcium Kids (VCSP22001B001) spike in 2025-Q4** (41 buyers) — possible seasonal gift/campaign push.

---

### Table 4 — Inflection Quarters (Shopee Focus)

| Period | Shopee New Custs | QoQ Change | Verdict |
|--------|:----------------:|:----------:|---------|
| 2024-Q1 | 130 | — | Baseline |
| 2024-Q2 | 274 | +111% | Strong recovery |
| **2024-Q3** | **325** | **+19%** | **PEAK** |
| 2024-Q4 | 246 | –24% | First drop |
| 2025-Q1 | 217 | –12% | Continued decline |
| **2025-Q2** | **106** | **–51%** | **CLIFF — structural break** |
| 2025-Q3 | 61 | –42% | Continued freefall |
| 2025-Q4 | 96 | +57% | Partial bounce |
| 2026-Q1 | 96 | flat | Plateau |
| 2026-Q2 | 105 | +9% | Slight uptick |

**Structural break = 2025-Q2.** The cliff was not a single-quarter snap but a 4-quarter fall: 325→246→217→106 (2024-Q3 to 2025-Q2). 2025-Q2 dropped –51% QoQ — the single worst quarter drop. 2025-Q3 continued falling to 61. Current level (96–105/qtr) is a plateau ~68% below 2024-Q3 peak.

**Is it a cliff or bleed?** Cliff: went from 325 (full velocity) to 61 in 3 quarters. A "slow bleed" would have been a multi-year gradual decline. This is a 3-quarter velocity crash.

---

### Table 5 — AOV & Order Frequency by Channel (Selected Quarters)

| Qtr | Channel | Orders | Unique Custs | Orders/Cust | AOV (K VND) | Net Rev (M) |
|-----|---------|:------:|:------------:|:-----------:|:-----------:|:-----------:|
| 2022-Q2 | Shopee | 276 | 235 | 1.17 | 1,432 | 395 |
| 2022-Q2 | Lazada | 36 | 28 | 1.29 | 1,768 | 64 |
| 2022-Q2 | Zalo | 1 | 1 | 1.0 | 16,489 | 17 |
| 2024-Q3 | Shopee | 445 | 368 | 1.21 | 1,002 | 446 |
| 2024-Q3 | Zalo | 21 | 21 | 1.0 | 2,404 | 51 |
| 2025-Q2 | Shopee | 165 | 142 | 1.16 | 995 | 164 |
| 2025-Q2 | Zalo | 9 | 8 | 1.13 | 7,125 | 64 |
| 2026-Q1 | Shopee | 180 | 126 | 1.43 | 1,526 | 275 |
| 2026-Q1 | Zalo | 16 | 15 | 1.07 | 4,853 | 78 |
| 2026-Q2 | Shopee | 199 | 147 | 1.35 | 1,217 | 242 |
| 2026-Q2 | Zalo | 13 | 11 | 1.18 | 8,152 | 106 |

**AOV story:**
- **Shopee AOV:** Dipped to 995K VND at 2024-Q3 peak volume (cheap SKU mix — Shark Cartilage, Cordyceps promos), now recovering to 1,217–1,526K VND as volume fell (price mix improving). Lower volume = higher AOV = premiumizing or promo pullback.
- **Zalo AOV:** Consistently 5–16× higher than Shopee (4,853–8,152K VND in 2026). Zalo is a high-value direct channel with fewer but larger orders. Growing from ~1% to 23% of B2C revenue with declining volumes.
- **Orders/customer frequency:** ~1.0–1.3 across all channels — essentially a single-order-per-quarter dynamic. Frequency has not changed meaningfully; volume is the only lever.

---

### Table 6 — Channel Concentration: Peak vs Now

**New Customer Mix:**

| Channel | Peak (22Q2-Q3) | % | Now (26Q1-Q2) | % |
|---------|:--------------:|:-:|:-------------:|:-:|
| Shopee | 400 | 68% | 201 | **87%** |
| Other-Mkt (Selly, Chiaki) | 94 | 16% | 1 | 0.4% |
| Lazada | 36 | 6% | 6 | 3% |
| Zalo | 7 | 1% | 12 | **5%** |
| Web/Direct | 17 | 3% | 7 | 3% |
| Facebook/Social | 10 | 2% | 4 | 2% |
| POS-Offline | 11 | 2% | 0 | 0% |
| Tiki | 12 | 2% | 0 | 0% |

**Revenue Mix:**

| Channel | Peak (22Q2-Q3) (M VND) | % | Now (26Q1-Q2) (M VND) | % |
|---------|-----------------------:|:-:|---------------------:|:-:|
| Shopee | 766 | 55% | 517 | **65%** |
| Zalo | 121 | 9% | 184 | **23%** |
| Lazada | 111 | 8% | 16 | 2% |
| Other-Mkt | 98 | 7% | 3 | 0% |
| Web/Direct | 94 | 7% | 59 | 7% |
| POS-Offline | 89 | 6% | 0 | 0% |
| Facebook/Social | 82 | 6% | 20 | 3% |

**Concentration now vs peak:**
- New customers MORE concentrated: Shopee 68%→87%. No meaningful alternative channel exists.
- Zalo punches above weight in revenue (5% of new custs, 23% of revenue) — high-value repeat/direct segment.
- Selly (16% of peak new customers) completely gone. Lazada, POS, Tiki all near-zero.
- 2022 had 7 channels contributing >1% each; 2026 has only 2 (Shopee + Zalo).

---

## (3) CAVEATS + EXCLUSIONS

| Item | Detail |
|------|--------|
| B2B/Wholesale excluded | scope_b2b=true (3,042 orders, 20B VND) + Dai Ly/Cho Si WHOLESALE channel excluded from B2C analysis |
| US/Export excluded | US channel (2,922 orders, 11B VND) excluded — separate economics |
| Internal/Other excluded | "Other" platform (Qua Tang, Uu dai NV, Test, Gosumo) excluded |
| Prior report discrepancy | Cohort report showed 550 peak (2022-Q2) — that included US+Wholesale+Internal customers. This report's B2C peak is 327 (2022-Q2) or 365 (2024-Q3). Both are valid; this report is the tighter retail-channel view. |
| Gateway SKU deduplication | When a customer had multiple products on their first order, all were counted (no dedup). Top-N shows coverage share not exclusive gateway. |
| 2026-Q2 incomplete | Data through 2026-06-21; Q2 ends 2026-06-30 — ~2 weeks of orders still coming. |
| fact_orders only (no fact_sales) for channel analysis | Channel dimension lives on fact_orders; SKU analysis joins fact_sales which has no scope flags. |
| POS-Offline channel | MM Market An Phu + Truong Dinh POS contributed new customers through 2023; ceased appearing 2024+. |

---

## (4) UNRESOLVED QUESTIONS (only the business owner can explain)

1. **Why did Shopee new customers collapse from 325 (2024-Q3) to 61 (2025-Q3)?** Was it: (a) budget/ad spend cut on Shopee platform, (b) Shopee algorithm change (fee increase, ranking demotion, flash-sale access revoked), (c) a competitor taking shelf space on the same keywords/categories? The data says Shopee lost 73% of new customer intake in 3 quarters — the cause is operational or strategic, not visible in sales data.

2. **What was Selly?** In 2022-Q2, Selly channel delivered 83 new customers (25% of all B2C new customers that quarter). It vanished completely by 2022-Q3 (5 customers) and 0 thereafter. Was this a promotions partnership/flash sale that was a one-time event? Did Selly platform shut down or was this relationship ended deliberately?

3. **Why did POS-Offline (retail store channel) peak in 2023-Q1 (38 new customers) and disappear by 2024?** Was MM Market An Phu POS location closed? Staffing changed? This was a 15–38 new-customers/quarter channel in 2022-2023.

4. **The 2024-Q3 Shopee peak (325 new customers) — what drove it?** Was there a marketing campaign, Shopee campaign sponsorship, flash sale, or new SKU launch that spiked this? Understanding what worked in 2024-Q3 is critical to reproducing it.

5. **Zalo trajectory:** Zalo is growing as a revenue channel (now 23% of B2C revenue vs 9% at peak) with very high AOV (8,152K VND in 2026-Q2). Is this intentional strategic shift toward direct/premium or organic behavior of the remaining loyal customer base? Is there a Zalo-driven CRM/OA strategy in place?

6. **Coix Beauty Tablets (VCSC23054B001) as 2026-Q2 gateway #1 (48 new buyers):** Is there an active Shopee promotion on this SKU driving the acquisition spike? The pattern mirrors the 2022-Q2 UV Care+ spike (cheap entry product driving volume). If so, is this deliberate acquisition strategy? What is the follow-on purchase rate for customers who enter via Coix Beauty?

7. **Shopee partial recovery (96→105 in 2026-Q1/Q2):** Is this organic or driven by specific campaigns? At current pace (~100–110/quarter vs 325 peak), recovering to peak would require 3× current acquisition rate. What is the plan?

8. **Bone's Calcium Kids (VCSP22001B001) spike 2025-Q4 (#1 gateway, 41 buyers):** Seasonal gifting event or deliberate push? Does this customer segment (parents buying for kids) have the same repeat profile as core supplement buyers?

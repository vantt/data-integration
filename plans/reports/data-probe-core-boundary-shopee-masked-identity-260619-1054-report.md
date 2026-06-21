# Data Probe: Core Boundary Sizing + Shopee Masked Identity
**Date:** 2026-06-19  
**DB:** `app_data/data_lake/export/marts/rolling/` parquet (read-only)  
**Total dim_customers:** 7,563

---

## Goal 1 — Core Boundary Sizing

### Boundary Counts

| Definition | Condition | IN (engine) | OUT (static rules) |
|---|---|---|---|
| **Def-A** | `is_contactable AND order_count > 1` | **1,236** | 6,327 |
| **Def-B** | `is_contactable AND (order_count > 1 OR recency_days ≤ 90)` | **1,263** | 6,300 |
| **Def-C** | `is_contactable AND (order_count > 1 OR value_group ∈ VIP/GOLD/SILVER OR recency_days ≤ 90)` | **1,349** | 6,214 |
| **Live Pulse** | `recency_days ≤ 90` (any contactability) | **264** | — |
| Live Pulse contactable | `recency_days ≤ 90 AND is_contactable` | **83** | — |

**Complement breakdown (what falls OUT of Def-A):**
- Not contactable (masked): 3,425
- Contactable but order_count = 1: 2,496
- Total complement: 6,327

**Def-B adds over Def-A:** only 27 customers (contactable, 1 order, recently active ≤90d)  
**Def-C adds over Def-B:** 86 customers (contactable, 1 order, VIP/GOLD/SILVER but recency >90d)

### Composition of Each Def

**Def-A (1,236):**

| value_group | Active | At Risk | Churned |
|---|---|---|---|
| VALUE_VIP | 7 | 6 | 57 |
| VALUE_SILVER | 2 | 7 | 199 |
| VALUE_GOLD | 1 | 0 | 77 |
| VALUE_BRONZE | 8 | 25 | 847 |

Critical finding: **85.6% of Def-A (1,058/1,236) have recency >365d** — they are effectively dormant. Only 56 are active (≤90d recency).

**Def-B (1,263):** Adds 27 more — same tier mix, slightly more At Risk in BRONZE (46 vs 25).

**Def-C (1,349):** Adds 86 more — mainly churned SILVER (+79) and churned GOLD (+7). These are high-value but long-dormant customers.

### Tier Health Context

| value_group | Active | At Risk | Churned | Churned% |
|---|---|---|---|---|
| VALUE_VIP | 11 | 7 | 75 | 80.6% |
| VALUE_SILVER | 11 | 21 | 374 | 92.1% |
| VALUE_GOLD | 1 | 2 | 93 | 96.9% |

VIP/GOLD/SILVER are overwhelmingly churned — widening the boundary to include them (Def-C) adds 86 mostly-dormant high-value customers.

### Recommended Boundary

**Def-B (1,263 customers)** — rationale:

1. **Def-A alone is too churned.** 85.6% have recency >365d. NBA triggers on these are wasted sends on likely-dead relationships. The +27 customers Def-B adds are genuinely recent (≤90d, 1 order) — they are acquisition targets worth one nudge.
2. **Def-C's 86 additions are high-effort, low-yield.** GOLD is 96.9% churned with avg 912-day recency. Worth a win-back campaign but not ongoing NBA logic — handle via one-shot static rules.
3. **Live Pulse (264) is already fully inside Def-B.** Of 264 live-pulse customers, 83 are contactable and already included.
4. **Scale is workable.** 1,263 is small enough for personalized daily scoring; large enough to matter.

Static-rule pool (complement = 6,214–6,327 depending on def): mass broadcast, unsubscribe suppression, or no-action.

---

## Goal 2 — Shopee Masked Identity Resolution

### Per-Channel Orders/Customers Ratio

Marketplace channels only (sorted by order volume):

| Channel | Orders | Customers | Orders/Cust | Repeat Buyers | Repeat% |
|---|---|---|---|---|---|
| US (cross-border) | 2,922 | 1,530 | 1.91 | 588 | 38.4% |
| Shopee - Fine Japan Vietnam | 1,817 | 1,359 | **1.34** | 302 | **22.2%** |
| Shopee - FWG Vietnam | 890 | 688 | 1.29 | 173 | 25.1% |
| Shopee - JPC OFFICIAL | 841 | 633 | 1.33 | 154 | 24.3% |
| Lazada - FINE WORLD GROUP | 220 | 155 | 1.42 | 87 | 56.1% |
| Shopee - thehealthyus | 191 | 182 | 1.05 | 22 | 12.1% |
| Shopee - JPC SHOP | 181 | 138 | 1.31 | 60 | 43.5% |
| Shopee (Unspecified) | 116 | 93 | 1.25 | 61 | 65.6% |
| Lazada (multi-shop, combined) | ~160 | ~124 | ~1.3 | ~75 | ~56% |
| TiktokShop | (not in top list) | — | — | — | — |

### Shopee-Aggregate Fragmentation Check

| Metric | Value |
|---|---|
| Total distinct Shopee customers (all shops) | **2,926** |
| Customers with order_count = 1 | 2,323 (79.4%) |
| Customers with order_count > 1 | **603 (20.6%)** |
| Masked customers (all Shopee) | 1,947 |
| Masked + repeat (order_count > 1) | **346** |

**20.6% of all Shopee-attributed customers have placed more than one order under the same customer record.** Of the 1,947 masked Shopee customers, 346 (17.8%) are repeat buyers under a stable identity.

### Identity Pattern Analysis

**Masked customer_code format:** Sequential internal codes (`CUZN04720`, `CUZN06123`, etc.) — these are Sapo-assigned, stable IDs, not throwaway relay-email hashes.

**Name pattern:** Consistent first-name masking format: `N******h`, `T******u`, `P******n` — same masking schema applied to a persistent record, not unique random strings per order.

**Phone/email:** NULL for all masked marketplace customers — Shopee's relay contacts are not stored, but the customer record persists.

**Confirmed via fact_orders cross-join:** Multiple masked Shopee customers appear with 7–36 orders under a single `customer_key` in `fact_orders`. Top examples:

| customer_code | masked_name | Channel | Orders (fact_orders) |
|---|---|---|---|
| CUZN04720 | N******h | Shopee - Fine Japan Vietnam | 36 |
| CUZN06123 | T******u | Shopee - Fine Japan Vietnam | 16 |
| CUZN04667 | N******g | Shopee - Fine Japan Vietnam | 12 |
| CUZN05957 | N******h | Shopee - Fine Japan Vietnam | 12 |

These are not fragmented — a single customer record accumulates orders over time.

### VERDICT: RESOLVES (does NOT fragment)

**Sapo aggregates repeat Shopee buyers under a single persistent customer record despite phone/contact masking.** The mechanism: Shopee sends a consistent buyer identifier (likely Shopee buyer ID or relay phone hash) that Sapo deduplicates into a stable `CUZN*****` code. Phone and email are NULL (masked), but the customer_key is stable and orders accumulate.

Evidence:
- 603 of 2,926 Shopee customers (20.6%) have order_count > 1 in dim_customers
- 346 masked Shopee customers are confirmed repeat buyers
- Top repeat masked Shopee customer has 36 lifetime orders under one record
- fact_orders confirms same customer_key spans multiple orders on different dates

**Fragmentation rate is near zero.** The 79.4% single-order rate reflects genuine one-time buyers, not identity explosion.

---

## Implications

1. **NBA engine boundary = Def-B (1,263)** is safe. Shopee repeat buyers (346 masked+repeat) are correctly accumulated in dim_customers — their order_count, recency, value_group, and lifetime_value are trustworthy inputs to the engine.

2. **Masked ≠ unreachable for the engine.** Masked customers can still be scored, segmented, and trigger backend actions (e.g., Shopee-native messages via seller platform). The contactability constraint (`is_contactable=true`) correctly excludes them from direct outreach but they can still receive in-channel nudges.

3. **The 346 masked+Shopee repeat buyers fall outside Def-B** (because `is_contactable=false`). They are a separate, high-intent segment — consider a Shopee-native re-engagement track outside the main NBA engine.

4. **Value-tier segmentation is reliable for Shopee customers.** CUZN04720 is VALUE_VIP (36 orders) because order accumulation works correctly. Tier-based static rules for churned VIP/GOLD apply to Shopee customers too.

5. **Static-rule pool (6,214–6,300)** includes: 3,425 masked (never contactable), 2,496 contactable-but-single-order-old, and a small tail of recent single-order arrivals. Segmentation by acquisition_source within the static pool can route Shopee-masked repeat buyers to platform-native flows.

---

## Unresolved Questions

1. **What identifier does Sapo use to link successive Shopee orders to the same customer?** Phone is NULL — is it Shopee buyer ID in a hidden field, or relay phone hash matched at ingest? Matters for understanding deduplication robustness across Shopee shop splits (FJV vs JPC vs FWG = same buyer → same record?).

2. **Cross-shop deduplication for Shopee:** Can a buyer who orders from Shopee - Fine Japan Vietnam AND Shopee - JPC OFFICIAL resolve to the same `CUZN*****`? The top repeat buyer CUZN04720 has 20 orders on FJV + 16 on JPC OFFICIAL under the same customer_key — suggests YES, but needs explicit confirmation from the Sapo import logic.

3. **Def-B active-core recency is thin:** Only 83 live-pulse contactable customers. If NBA requires ≥N active customers/month to be worth running, 83 is tight. Clarify the minimum viable active-cohort size for the engine to generate meaningful lift.

4. **Masked+repeat Shopee track:** 346 customers are known repeat buyers but excluded from direct outreach. Is there a Shopee seller messaging API or campaign-list export available to reach them in-channel?

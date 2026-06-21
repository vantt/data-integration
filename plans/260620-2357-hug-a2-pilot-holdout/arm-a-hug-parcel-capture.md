# Arm A — Hug Parcel Capture (Zone 1 Active)

## Overview

Reactive identity capture: every qualifying outbound parcel gets a Hug tem. Treatment group sees HUG50 offer on opt-in landing; control group receives no tem (or a blank tem variant — see Open Question #2 in plan.md). Measures incremental opt-in and repeat purchase driven by the offer.

---

## Eligibility & Exclusion Rules

Applied in order before cohort assignment:

| Rule | Filter | Source |
|------|--------|--------|
| Zone 1 only | `recency_days ≤ 90` | `mart_customer_tier.recency_days` |
| Masked only | `source_contact_quality = 'masked'` | `mart_customer_tier` |
| Repeat buyers | `order_count ≥ 2` | `mart_customer_tier` |
| Exclude B2B/export | `customer_key NOT IN (<15-account list>)` | Manual list — lock before launch |
| AOV gate | `lifetime_value / order_count ≥ 1,000,000` VND | `mart_customer_tier` |
| Exclude zero-net-revenue | `lifetime_value > 0` | `mart_customer_tier` |

**Expected eligible N after filters:** ~62 marketplace Zone 1 → after AOV≥1M gate → estimated **~45–55** (Bucket C–F accounts; Bucket A/B excluded or offered reduced voucher per recommendation).

For the pilot, target simple: **AOV ≥ 1M only (Buckets C, D, E, F) = estimated ~40 eligible customers.**

---

## Randomization

- Method: simple deterministic hash on `customer_key` mod 100 → treatment if hash < 65, control if ≥ 65.
- Ratio: **~65% treatment / ~35% control** → ~40 T / ~22 C given N≈62.
- Assignment frozen at pilot start date; new Zone-1 entrants during the window added to treatment pool (control saturates faster with small N).
- Record: `hug_pilot_arm = 'A'`, `hug_pilot_group = 'treatment' | 'control'` in cohort label table (see instrumentation-tracking.md).

**Why hash-based:** reproducible without a separate randomization service; deterministic audit trail; no re-randomization risk if Dagster refresh re-runs.

---

## Treatment vs Control Definition

| Group | Action | What customer sees |
|-------|--------|--------------------|
| **Treatment** | Warehouse attaches Hug tem to every outbound parcel for this customer | QR → opt-in landing → "Nhận HUG50 giảm 50K đơn ≥1M" → Zalo/SĐT capture → code revealed |
| **Control** | No tem attached (or blank tem with no offer — TBD per Open Q#2) | Natural reorder behavior; no Hug intervention |

**Offer detail (Treatment):**
- Code: `HUG50` (Sapo coupon, shared per-campaign, `once_per_customer = true`, min order 1,000,000 VND)
- Value: 50,000 VND off
- Expiry: 60 days from issuance date (matches measurement window)
- Zalo OA follow required for issuance (identity capture purpose)

---

## Primary & Secondary Metrics

### Primary
| Metric | Definition | Data source |
|--------|-----------|-------------|
| **Opt-in rate** | `# customers who complete Zalo/SĐT identity capture / # treatment customers with ≥1 parcel shipped` | `/hug/vouchers` ledger; `hug_identities` table |
| **Repeat purchase within 60d** (binary, per customer) | Customer has ≥1 order in `fact_orders` in the 60-day window post-pilot-start, for BOTH groups | `fact_orders.ordered_at`, `fact_orders.customer_id` joined to cohort |

### Secondary
| Metric | Definition | Data source |
|--------|-----------|-------------|
| Redemption rate | `# HUG50 redemptions / # vouchers issued` | `fact_orders.order_coupon_code = 'HUG50'` + `crm_hug_voucher` ledger |
| Incremental CM | `(treatment group CM earned) − (control group CM) − (voucher cost redeemed)` | `fact_orders.contribution_margin` by cohort; exclude zero-net-revenue orders |
| Scan rate | `# QR scans / # tems shipped` | Edge `hug_scans` log (Cloudflare D1 or crm.db event log) |
| Time-to-opt-in | Days from parcel ship date to identity capture | `hug_identities.captured_at` vs `fact_orders.shipped_at` |

**Exclude from all metric calcs:** orders where `net_revenue = 0` or customer_key in B2B exclusion list.

---

## Sample Size & Statistical Power

| Parameter | Value |
|-----------|-------|
| N treatment | ~40 |
| N control | ~22 |
| Total | ~62 |
| Control base repeat rate (assumed) | ~40% (Zone 1 active; median gap 7d means high natural reorder) |
| Minimum detectable effect (80% power, α=0.10 one-tailed) | ~20 percentage-point lift (40% → 60%) |
| **Honest assessment** | **Underpowered for statistical significance.** This is a directional pilot, not an RCT. Report point estimates + 80% CI; do not claim p<0.05 unless effect is very large. |

**Why proceed anyway:** We have no prior opt-in rate data at all. Even a directional read (opt-in 30% vs 5%, or repeat rate 55% vs 40%) informs the scale decision. The cost of NOT running a control is making scale decisions on biased data (many Zone 1 customers would reorder anyway).

---

## Measurement Window

- **Start:** day pilot goes live (tem attachment begins)
- **Primary read:** Day 60 (opt-in rate + repeat purchase)
- **Confirmation read:** Day 90 (tail purchases; voucher expiry check)
- **Do not extend:** if no signal by Day 90, document as inconclusive, not failure.

---

## Decision Gate

Read at Day 60–90:

| Outcome | Threshold | Decision |
|---------|-----------|----------|
| **Scale** | Opt-in ≥20% AND repeat-60d treatment > control by ≥10pp AND net incremental CM > 0 | Expand to all Zone 1 eligible; brief Arm B learnings |
| **Iterate** | Opt-in ≥10% but lift <10pp OR voucher cost > incremental CM | Adjust offer (raise to % or 100K); re-test with larger N when Zone 2 reactivations join Zone 1 |
| **Kill offer, keep tem** | Opt-in <10% | Tem insert alone is cost-free; keep phủ tem but remove offer; revisit offer design |
| **Kill tem** | Opt-in <5% AND repeat rate indistinguishable | Evidence that Hug parcel capture has no signal; stop investment |

**Gate requires:** Data team readout report (see operations-runbook.md), not Marketing self-assessment.

---

## Operational Requirements (Warehouse)

- Brief kho: **every outbound parcel for treatment-group customer_keys gets a Hug tem attached.** Control group: no tem.
- Provide warehouse a printed/digital list: `customer_key → treatment | control` (or SKU-level flag from WMS if available).
- If warehouse cannot implement per-customer differentiation: apply tem to ALL qualifying parcels (treatment only), abandon control arm → metric becomes opt-in rate only (no incrementality measurement). Document this degradation.
- **Tem coverage target:** ≥95% of treatment-group outbound orders get a tem within the 60-day window.

---

## Data Flow

```
outbound parcel (treatment) → Hug QR tem attached
    → customer scans QR → Edge Worker (hug.fjp.vn)
    → opt-in landing → Zalo/SĐT capture
    → /admin/refresh (nightly) → identity resolution → hug_identities
    → voucher issuance → crm_hug_voucher ledger
    → customer uses HUG50 on Sapo → fact_orders.order_coupon_code = 'HUG50'
    → /admin/refresh redeem matcher → crm_hug_voucher.redeemed_at
    → Data team joins cohort table → incremental CM calc
```

Control group data flow:
```
control customer → no tem → natural reorder behavior
    → fact_orders.ordered_at (no coupon code)
    → Data team joins cohort table → control repeat rate
```

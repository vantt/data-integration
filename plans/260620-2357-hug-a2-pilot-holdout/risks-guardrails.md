# Risks & Guardrails

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| R1 | **Small N makes results inconclusive** — Arm A N≈62, Arm B N≈200; neither is powered for <10pp effects | High | Medium | Accept as directional pilot. Report point estimates + 80% CI. Decision gates use pre-agreed thresholds (not p-values). Frame to leadership upfront: this is calibration, not proof. |
| R2 | **Shopee Chat Broadcast not available on VN portal** | Medium | High (kills Arm B) | Pre-launch check (Week 1 checklist item #1). If unavailable: Arm B becomes passive Repeat Buyer Voucher only; remove R estimate from forward model; escalate to leadership. |
| R3 | **Warehouse cannot implement per-customer tem differentiation** | Medium | Medium | Fallback: attach tems to ALL qualifying parcels (treatment only, abandon control). Arm A becomes opt-in rate measurement only — no incrementality. Document degradation explicitly. |
| R4 | **Cannibalization: control customers see HUG broadcast via other channels** | Low | Medium | Keep Arm A control customers off all Hug marketing during the 90-day window. Cross-check: if control customer_key appears in Arm B treatment list, flag and remove from Arm A control (cannot be in two treatment arms). |
| R5 | **Shopee ToS violation — off-platform solicitation** | Low | High (shop suspension) | Strict message framing review before send (restock only, no mention of Zalo/direct). Tem insert is physical, separate from Shopee chat. Legal review of broadcast copy if uncertain. |
| R6 | **CM data quality: zero-net-revenue artifact distorts incremental CM calc** | High | High | Hard filter: `net_revenue > 0` on ALL metric queries. B2B exclusion list applied at cohort assignment AND query time. Never report aggregate CM without this filter. |
| R7 | **HUG50 / HUGVIP coupon misconfigured in Sapo** | Low | High | Pre-launch verification (checklist). Confirm `once_per_customer=true` and min-order gate before any parcel ships or broadcast sends. If `once_per_customer` is not enforced: one customer could redeem multiple times → voucher cost spikes. |
| R8 | **Opt-in landing broken (Zalo OA / env var)** | Low | High (kills Arm A measurement) | `HUG_ZALO_OA_URL` env var verification in pre-launch checklist. Day-2 smoke test: scan one QR manually, verify landing page loads and follow CTA works. |
| R9 | **B2B exclusion list incomplete** — additional export accounts not yet identified | Medium | Medium | Use `net_revenue > 0` filter as backstop in all CM calculations. Flag any customer_key with `contribution_margin < −500K/order` for manual review before they affect metrics. |
| R10 | **Arm B reactivation counted as organic** — customer would have re-ordered anyway (organic Zone 2 return) | Medium | Medium | Control arm exists precisely for this. If control R ≈ treatment R → broadcast has no incremental effect. Do not cancel control arm even if it feels wasteful. |
| R11 | **Voucher expiry mismatch** — customer opts in on Day 55, HUG50 expires Day 60 → no time to use | Low | Low | Voucher expiry set from **issuance date** (not pilot start). 60-day window per voucher, not per pilot. Verify in `crm_hug_voucher.expires_at` logic. |

---

## Small-N Caveats (communicate to leadership)

State explicitly in every readout report:

> "Arm A (N≈62) and Arm B (N≈200) are underpowered for statistical significance at conventional thresholds. Results are directional. An effect must be large (≥12–20 percentage points) to be detectable above noise. Small observed differences (e.g., treatment R=10% vs control R=7%) cannot be interpreted as evidence of no effect — they are simply unmeasurable at this scale. Decisions based on this pilot should be treated as informed bets, not proven facts. Scale decisions trigger a larger, better-powered follow-on measurement."

---

## Cannibalization Guard

Customers must not appear in both Arm A treatment and Arm B treatment simultaneously:

- Arm A target = Zone 1 (recency ≤90d)
- Arm B target = Zone 2 (recency 91–720d)
- Zones are mutually exclusive by definition at cohort-freeze date.
- **Edge case:** a Zone 2 customer reorders during the pilot window → their recency drops to ≤90d → they become Zone 1. They should NOT be retroactively added to Arm A. Cohort assignment is frozen at pilot start.

---

## Data Quality Guardrails

Apply these filters in every metric query — no exceptions:

```
1. net_revenue > 0                                          (exclude zero-revenue artifact orders)
2. customer_key NOT IN (B2B exclusion list, 15 accounts)    (exclude export/internal misclassified)
3. customer_key NOT IN (CHANNEL_OTHER outlier list, ~3)     (Fine Japan-USA + negative-CM outliers)
4. order_count >= 2                                         (pilot targets repeat buyers only)
5. contribution_margin IS NOT NULL                          (exclude orders with missing COGS)
```

Failure to apply filter #1 alone introduces ~−23.7B VND of CM distortion across the full warehouse (per margin anomalies root-cause report). Even if only a few of the 3,544 artifact orders belong to pilot cohort customers, they will corrupt the incremental CM calculation.

---

## Shopee Spam / ToS Limits

| Limit | Value | Source |
|-------|-------|--------|
| Max broadcast per buyer per day | 1 message | Shopee Chat Broadcast policy |
| Max broadcast per buyer per week | 2 messages | Shopee (hard enforced) |
| Max total from all sellers per buyer per week | 5 messages | Shopee buyer-side cap |
| Shopee API for messaging | NOT available | No public endpoint; manual only |

**Do not attempt to work around the 2msg/week cap** (e.g., sending from multiple shop accounts). Shopee rate-limits at the buyer ID level, not the shop level. Circumvention attempts risk shop suspension.

---

## What We Learn That Unlocks Scale

This pilot answers exactly two questions the business cannot currently answer from existing data:

### Question 1 (Arm A): Does the Hug tem + offer generate meaningful opt-in?

- **Learn:** opt-in rate (de-mask rate) for Zone 1 active customers.
- **Unlocks:** confidence in infrastructure; validates QR→Zalo→identity pipeline at real scale.
- **Scale trigger:** opt-in ≥20% + positive incremental CM → roll out to 100% of qualifying masked outbound parcels (not just Zone 1; eventually Zone 2 reactivations as they come back).

### Question 2 (Arm B): What is the real reactivation rate R for Zone 2 dormant?

- **Learn:** first empirical R estimate for this specific customer base (no prior data).
- **Unlocks:** the forward annual opportunity model (`259 × R × orders/yr × 545K VND`). Currently R is a 10–30% industry guess. A real R — even directional — collapses the scenario range and justifies (or kills) investment in Shopee broadcast as a channel.
- **Scale trigger:** R ≥15% treatment vs ≤5% control → broadcast to full Zone 2 eligible, build into quarterly marketing calendar.

**What we do NOT learn from this pilot:**
- Statistical proof of causality (too small N).
- Long-term retention of reactivated customers (need 12-month follow-on cohort).
- Offer optimization (this pilot uses a single offer level; A/B offer testing is a Phase 2 experiment).
- Effect on Zone 3 lost customers (excluded by design; require different channel not yet available).

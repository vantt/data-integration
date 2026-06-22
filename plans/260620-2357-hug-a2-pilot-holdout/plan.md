---
title: "Hug A2 Pilot — Holdout Experiment (Zone 1 + Zone 2)"
description: "Measured rollout with control arms to learn opt-in rate, redemption, reactivation R, and incrementality before scaling."
status: pending
priority: P1
effort: 8w
branch: main
tags: [hug, a2, pilot, holdout, marketing, experiment]
created: 2026-06-21
---

## Context

- Strategy doc: `docs/finejapan-growth-strategy/hug-campaign-overview-for-leadership.md`
- Segment data (live): `plans/reports/analytics-260620-2213-masked-repeat-economics-reachability-report.md`
- Shopee messaging: `plans/reports/researcher-260620-2217-shopee-seller-messaging-masked-buyers-re-engagement-report.md`
- Tech build (DONE): `plans/260620-1408-crm-hug-voucher-a2-golive/plan.md`

## Experiment Arms

| Arm | Segment | N (treat / ctrl) | Primary metric | Read window |
|-----|---------|-------------------|----------------|-------------|
| [A — Hug parcel capture](arm-a-hug-parcel-capture.md) | Zone 1 active ≤90d, AOV≥1M, excl B2B | ~40 T / ~22 C | Opt-in rate + repeat purchase 60d | 60–90 days |
| [B — Shopee Chat Broadcast](arm-b-shopee-broadcast.md) | Zone 2 dormant 91–720d marketplace, ~200 eligible | ~130 T / ~70 C | Reactivation rate R (purchase 120d) | 120–180 days |

## Section Files

| File | Purpose |
|------|---------|
| [arm-a-hug-parcel-capture.md](arm-a-hug-parcel-capture.md) | Eligibility, randomization, metrics, decision gate |
| [arm-b-shopee-broadcast.md](arm-b-shopee-broadcast.md) | Eligibility, broadcast runbook, metrics, decision gate |
| [instrumentation-tracking.md](instrumentation-tracking.md) | Cohort labels, data sources, readout queries |
| [operations-runbook.md](operations-runbook.md) | Owner assignments, weekly cadence, escalation |
| [risks-guardrails.md](risks-guardrails.md) | Small-N caveats, ToS, data quality |

## Timeline (high-level)

```
Week 1    Setup & baseline: cohort label, Sapo HUG50 code, Shopee broadcast prep
Week 2    Arm A live (tem on qualifying parcels); Arm B broadcast sent
Week 4    Arm A interim read (opt-in rate, first repeats appearing)
Week 8    Arm A primary read (60d window complete); decision gate A
Week 12   Arm B interim read (reactivation starting)
Week 20   Arm B primary read (120d window + 60d tail); decision gate B
```

## Success Criteria Summary

- Arm A unlocks scale if: opt-in ≥20%, repeat-60d treatment vs control lift ≥10pp, incremental CM > voucher cost.
- Arm B unlocks scale if: R ≥15% treatment vs ≤5% control, incremental CM > broadcast effort cost.
- Either arm → kill/iterate if: opt-in <10% (A) or R <8% (B) or CM negative.

## Open Questions

1. **Offer level AOV≥1M**: flat 50K VND (token) vs % (stronger lever)? 50K = 3.5% of 1.4M median — token only; reactivation for Zone 2 dormant may need % or tiered gift. Decide before Arm A launch.
2. **Control-group ethics (tem withholding)**: withholding Hug tem from control customers means they never see the offer — acceptable for a short pilot? Or give them a no-offer tem (scan→no voucher) to measure scan rate independently?
3. **Shopee broadcast capability final confirmation**: Chat Broadcast "Repeat Buyers" audience segment confirmed available on Shopee VN portal? 720-day window confirmed? Rate limit 2 msg/buyer/week confirmed for VN?
4. **Zalo OA / landing env var**: `HUG_ZALO_OA_URL` set in production `.env`? Needed for opt-in landing CTA to function.
5. **B2B account list (15 accounts)**: exact `customer_key` list locked for exclusion filter? Must be applied before cohort assignment, not after.
6. **AOV <500K exclusion vs holdout sub-group**: 97 Bucket A accounts — exclude entirely from both arms, or include in control-only to track organic behavior without offer?

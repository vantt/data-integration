# Operations Runbook & Owners

## Owner Matrix

| Domain | Owner | Responsibilities |
|--------|-------|-----------------|
| **Marketing** | Marketing lead | Offer rules, Sapo coupon creation, Shopee broadcast content, Zalo OA setup, Follow Prize campaign, decision gate sign-off |
| **Warehouse** | Warehouse supervisor | Tem attachment coverage (treatment arm A), per-customer differentiation from cohort list, coverage reporting |
| **Data** | Data analyst | Cohort label table creation, weekly readout queries, decision gate reports, exclusion filter enforcement |
| **Tech** (monitoring only) | Backend dev | Confirm `/admin/refresh` nightly run healthy, `hug_identities` table accumulating, `/hug/vouchers` ROI screen readable — no code changes required |

---

## Pre-Launch Checklist (Week 1)

### Marketing
- [ ] Confirm Shopee Chat Broadcast "Repeat Buyers" audience + 720-day window available on VN portal
- [ ] Create Sapo coupon `HUG50` (50K, min 1M, once_per_customer, 60-day expiry)
- [ ] Create Sapo coupon `HUGVIP` (50K, min 1M, once_per_customer, 120-day expiry)
- [ ] Draft Shopee broadcast message (restock framing, include HUGVIP code, Vietnamese, ≤200 chars)
- [ ] Create Shopee Repeat Buyer Voucher (passive, same terms as HUGVIP, no quota cost)
- [ ] Confirm Zalo OA is live and `HUG_ZALO_OA_URL` env var set in production `.env`
- [ ] Chốt offer level: 50K flat confirmed for AOV≥1M? Or escalate to leadership for % option?
- [ ] Export Shopee Seller Center order list (CSV, past 24 months) → hand to Data for cross-match

### Data
- [ ] Confirm B2B exclusion list (15 account `customer_key`s) locked in writing
- [ ] Confirm zero-net-revenue outlier exclusion list (~3 accounts)
- [ ] Run cohort assignment script → populate `hug_pilot_cohorts` in crm.db
- [ ] Verify row counts: Arm A ~62 total (~40T/~22C), Arm B ~200 total (~130T/~70C)
- [ ] Cross-match Shopee `buyer_username` export to Arm B treatment cohort → produce treatment send list
- [ ] Verify `HUG50` and `HUGVIP` codes exist in Sapo and are active
- [ ] Baseline snapshot: run weekly readout query on Day 0 (pre-launch); record 0 opt-ins, 0 repeats as baseline

### Warehouse
- [ ] Receive Arm A treatment customer_key list from Data
- [ ] Brief picking/packing team: attach Hug tem to every outbound parcel for treatment customers
- [ ] Confirm tem supply (rolls) sufficient for ~60-day window for ~40 treatment accounts
- [ ] Establish coverage reporting: daily count of treatment parcels shipped with tem attached

### Tech (verify only — no code changes)
- [ ] Confirm `/admin/refresh` last successful run (check admin logs)
- [ ] Confirm `/hug/campaigns` A2 campaign exists and is active
- [ ] Confirm `hug_identities` table schema matches expected columns (customer_id, captured_at, etc.)
- [ ] Confirm `/hug/vouchers` ROI screen loads without error

---

## Launch Sequence (Day 1)

1. **Data:** confirm cohort table written, row counts verified.
2. **Warehouse:** begin tem attachment for Arm A treatment parcels.
3. **Marketing:** send Arm B broadcast Batch 1 to treatment `buyer_username` list (Shopee Seller Center). Screenshot delivery confirmation.
4. **Data:** record `broadcast_date = today` as Arm B anchor in readout template.
5. **Marketing:** activate Shopee Repeat Buyer Voucher (passive, runs automatically).
6. **All:** confirm in team channel — pilot is live.

---

## Week 1 Follow-Up (Day 7–8)

- **Marketing:** check Shopee broadcast delivery stats (Seller Center analytics). If <70% delivered, investigate (inactive accounts, quota issues) and document.
- **Marketing:** send Arm B broadcast Batch 2 follow-up to non-converted treatment customers.
- **Warehouse:** report tem attachment count for Week 1 outbound parcels.
- **Data:** run first interim readout query; share to team channel (expect near-zero signal this early; confirm data pipeline is working).

---

## Weekly Readout Cadence

Every Friday, Data runs the readout queries and produces a short Markdown report saved to `plans/260620-2357-hug-a2-pilot-holdout/reports/readout-YYYYMMDD.md`.

Report template (keep to one page):

```
## Hug A2 Pilot — Weekly Readout YYYY-MM-DD (Week N)

### Arm A (Hug Parcel Capture) — Day X of 90
| Metric | Treatment (N=~40) | Control (N=~22) |
|--------|-------------------|-----------------|
| Opt-in rate | X% | — |
| Repeat buyers (60d) | X% | X% |
| HUG50 redemptions | N | — |
| CM (treatment) | XVND | — |
| CM (control) | — | XVND |
| Tem coverage (this week) | X% of outbound parcels | — |

### Arm B (Shopee Broadcast) — Day X of 180
| Metric | Treatment (N=~130) | Control (N=~70) |
|--------|--------------------|--------------------|
| Reactivation rate R | X% | X% |
| HUGVIP redemptions | N | — |
| CM (treatment) | XVND | XVND |

### Flags / Actions
- [any anomalies, missing data, warehouse coverage gaps]

### Next checkpoint
- [what to watch for next week]
```

---

## Decision Gate Process

### Arm A Gate (Day 60–90)

1. **Data** produces `decision-gate-arm-a-YYYYMMDD.md` with: point estimates, 80% CI, incremental CM calc.
2. **Marketing + Leadership** review within 3 business days.
3. **Decision recorded in writing** (Slack message or doc comment): Scale / Iterate / Kill — with explicit reasoning.
4. If Scale: Marketing briefs Warehouse for full Zone 1 rollout; Data expands cohort table.
5. If Iterate: Marketing proposes offer change; new mini-pilot within existing framework.
6. If Kill: Warehouse stops tem attachment for Hug offer; tem infrastructure kept but offer removed.

### Arm B Gate (Day 120–180)

Same process. Additional consideration: if Arm A scaled, Arm B results inform whether to combine Shopee broadcast + Hug tem as a sequential funnel (broadcast → reorder → tem capture).

---

## Escalation

| Situation | Escalate to | Action |
|-----------|------------|--------|
| Shopee Chat Broadcast not available on VN portal | Marketing → Leadership | Kill Arm B; document; run passive Repeat Buyer Voucher only |
| Warehouse cannot implement per-customer tem differentiation | Warehouse → Data → Leadership | Abandon control arm; Arm A becomes opt-in rate measurement only (no incrementality) |
| `/admin/refresh` fails for >2 consecutive days | Tech | Investigate; voucher issuance delayed but not lost — identity records queue in `hug_identities` |
| `HUG50` or `HUGVIP` coupon missing/inactive in Sapo | Marketing + Tech | Block pilot launch until resolved |
| Arm A opt-in rate = 0% after Week 2 (≥5 tems shipped) | Data → Marketing | Check landing page URL in QR, Zalo OA active, `HUG_ZALO_OA_URL` env var |

# Arm B — Shopee Chat Broadcast (Zone 2 Dormant)

## Overview

Proactive reactivation: send a Shopee Chat Broadcast to dormant masked-repeat customers (91–720 days recency) with a restock-reminder framing + shop voucher. Measures reactivation rate R (first purchase within 120 days). Underpowered for significance — purely directional; the primary goal is a first real R estimate to anchor forward-opportunity sizing.

---

## Eligibility & Exclusion Rules

Applied in order before cohort assignment:

| Rule | Filter | Source |
|------|--------|--------|
| Zone 2 only | `recency_days > 90 AND recency_days ≤ 720` | `mart_customer_tier.recency_days` |
| Masked only | `source_contact_quality = 'masked'` | `mart_customer_tier` |
| Repeat buyers | `order_count ≥ 2` | `mart_customer_tier` |
| Marketplace channel | `primary_channel = 'CHANNEL_MARKETPLACE'` | `mart_customer_tier` *(Shopee Chat Broadcast is marketplace-only tool)* |
| Exclude B2B/export | `customer_key NOT IN (<15-account list>)` | Manual list — same list as Arm A |
| Exclude zero-net-revenue outliers | Remove `customer_key` for Fine Japan-USA + CHANNEL_OTHER/SOCIAL negative-CM outliers (~3 accounts) | Manual exclusion from reachability report |
| Exclude AOV <500K (Bucket A) | `lifetime_value / order_count < 500,000` → exclude | Negative order-level CM; voucher ROI negative |

**Expected eligible N after filters:** ~259 marketplace Zone 2 → minus ~57 Bucket A (estimated) → **~200 eligible**. Use ~200 as working number; verify from live mart before launch.

---

## Randomization

- Method: deterministic hash on `customer_key` mod 100 → treatment if hash < 65, control if ≥ 65.
- Ratio: **~65% treatment / ~35% control** → **~130 T / ~70 C** from N≈200.
- Assignment frozen at broadcast send date; no re-assignment if broadcast is sent in batches.
- Record: `hug_pilot_arm = 'B'`, `hug_pilot_group = 'treatment' | 'control'` in cohort label table.

**Important:** Shopee Chat Broadcast does not allow per-customer audience exclusion by external ID. Workaround: build the treatment list from the cohort table first, then send broadcast targeting only those `buyer_username` values (export from Seller Center order list, cross-match to cohort, send manually or via template). Control group = no broadcast sent (passive observation).

---

## Treatment vs Control Definition

| Group | Action | What customer sees |
|-------|--------|--------------------|
| **Treatment** | Shopee Chat Broadcast message sent; Repeat Buyer Voucher active in app | In-platform message + passive voucher display in Shopee app |
| **Control** | No broadcast; no special voucher targeting | Natural dormant behavior; may still discover shop organically |

**Content framing (Treatment):**
- Message type: restock reminder — NOT off-platform solicitation (ToS-safe)
- Sample Vietnamese copy: *"Chào bạn! Sản phẩm [category] vừa nhập hàng mới. Dùng mã **HUGVIP** giảm 50K cho đơn từ 1 triệu — hàng có hạn, đặt sớm bạn nhé!"*
- Voucher attached: `HUGVIP` (separate code from HUG50 to distinguish Arm B redemptions in fact_orders)
- Offer value: 50K flat (AOV ≥1M gate enforced via Sapo coupon min-order rule)
- Expiry: 120 days from send date (matches measurement window)
- Broadcast batch limit: 2 messages/buyer/week (Shopee hard limit); send batch 1 on Day 1, batch 2 follow-up on Day 8 if no conversion.

**Follow Prize (optional parallel):**
- Run "Follow + nhận voucher" campaign concurrently to build follower base for future broadcasts.
- Do NOT credit Follow Prize conversions as Arm B reactivations — track separately.

---

## Primary & Secondary Metrics

### Primary
| Metric | Definition | Data source |
|--------|-----------|-------------|
| **Reactivation rate R** | `# customers with ≥1 order in fact_orders within 120 days of broadcast date / # customers in group` | `fact_orders.ordered_at` joined to cohort; compare treatment vs control |

### Secondary
| Metric | Definition | Data source |
|--------|-----------|-------------|
| Redemption rate | `# HUGVIP redemptions / N treatment` | `fact_orders.order_coupon_code = 'HUGVIP'` |
| Incremental CM | `(treatment reactivated CM) − (voucher cost) − (control CM in same window)` | `fact_orders.contribution_margin` by cohort; zero-net-revenue orders excluded |
| Time-to-reactivation | Days from broadcast send to first post-broadcast order | `fact_orders.ordered_at − broadcast_date` |
| Reactivation order frequency | Orders per reactivated customer in 120-day window | `fact_orders` grouped by customer, window-bounded |
| CM per reactivated order | Actual vs 545K/order assumption used in forward-opportunity model | `contribution_margin / order_count` per reactivated customer |

**HUGVIP vs HUG50:** separate coupon codes are essential — they are the only way to distinguish Arm A vs Arm B redemptions in `fact_orders.order_coupon_code` without a join to the cohort table. Create both in Sapo admin before launch.

---

## Sample Size & Statistical Power

| Parameter | Value |
|-----------|-------|
| N treatment | ~130 |
| N control | ~70 |
| Total | ~200 |
| Control base reactivation rate (assumed) | ~5% organic (Zone 2 dormant; most are churned) |
| Target treatment reactivation rate (base case) | ~17% (R=17%) |
| Minimum detectable effect (80% power, α=0.10 one-tailed) | ~12 percentage-point lift |
| **Honest assessment** | **Directional only.** 130T/70C gives ~80% power to detect a 12pp lift — achievable if broadcast genuinely moves the needle. Marginal effects (<8pp) will not be distinguishable from noise. Report R with 80% CI. |

**Why the R estimate matters:** Forward annual CM formula = `259 × R × orders/yr × 545K`. The difference between R=10% and R=20% is ~14M VND vs ~28M VND/year. Getting even a directional read on R is worth the effort cost.

---

## Measurement Windows

| Checkpoint | Purpose |
|-----------|---------|
| Day 14 | Confirm broadcast delivered (Shopee Seller Center delivery stats); abort/retry if <70% delivered |
| Day 30 | Early reactivation read (expect <5% of conversions by now; sanity check) |
| Day 60 | Interim R read; flag to leadership if treatment R already >15% |
| Day 120 | **Primary read** — reactivation rate, redemption, incremental CM |
| Day 180 | **Confirmation read** — tail orders, voucher expiry validation, final CM tally |

---

## Decision Gate

Read at Day 120–180:

| Outcome | Threshold | Decision |
|---------|-----------|----------|
| **Scale broadcast** | Treatment R ≥15% AND control R ≤5% AND incremental CM > voucher cost | Run full Zone 2 broadcast (all ~200 eligible); increase broadcast frequency to 2×/week |
| **Iterate offer** | R ≥8% but incremental CM negative (voucher too rich vs reactivated CM) | Reduce offer to 30K or apply % cap; re-test |
| **Iterate message** | R <8% but scan-rate / click-rate reasonable (Shopee provides) | Message framing wrong; test urgency/product hook variant |
| **Kill broadcast** | Treatment R ≤5% (indistinguishable from control) | Shopee broadcast does not move this audience; reallocate to GMV Max / Follow Prize only |

**Kill threshold rationale:** 5% is the assumed organic base rate. If treatment can't beat that, the broadcast has no incremental value.

---

## Shopee Broadcast Operational Runbook

Pre-launch (Day −7 to 0):

1. **Verify platform capability** (Marketing, final check):
   - Log into Shopee Seller Center VN → Marketing Centre → Chat Broadcast
   - Confirm "Repeat Buyers" audience segment is available
   - Confirm 720-day buyer window is accessible (not just 90-day)
   - Confirm rate limit displayed (expect 2 msg/buyer/week)
   - **If any of these are absent: STOP — escalate to leadership before proceeding.**

2. **Export buyer list** from Seller Center (all orders, past 24 months) → CSV with `buyer_username`.

3. **Cross-match to cohort table** (Data): join `buyer_username` to `mart_customer_tier` via Shopee order ID or username mapping to isolate treatment group `buyer_usernames`. Exclude control group from send list.

4. **Create Sapo coupon `HUGVIP`**: min order 1,000,000 VND, 50K off, `once_per_customer = true`, 120-day expiry. Distinct from HUG50.

5. **Draft broadcast message** (Marketing): Vietnamese, restock framing, include `HUGVIP` code and expiry date. Max ~200 chars (Shopee UI limit).

6. **Create Repeat Buyer Voucher** in Seller Center (passive, no quota cost): same 50K/1M gate, same expiry. Runs parallel to broadcast.

Launch (Day 1):

7. **Send Batch 1 broadcast** to treatment `buyer_username` list. Screenshot delivery confirmation from Seller Center.

8. **Record send timestamp** → anchor for all measurement windows.

Day 8:

9. **Send Batch 2 follow-up** to non-converted treatment customers (Shopee 2msg/week quota now refreshed).

---

## ToS Compliance Checklist

| Item | Status | Notes |
|------|--------|-------|
| Message content = restock/product reminder | Required | NOT "buy from us on Zalo/direct" — that triggers off-platform solicitation ban |
| No explicit request to transact outside Shopee | Required | Hug tem opt-in is NOT mentioned in the broadcast message |
| Voucher attached is a Shopee voucher (not Sapo code) | Preferred | Use Shopee Repeat Buyer Voucher for in-platform passive; use `HUGVIP` only in broadcast text as a restock hook. Clarify which voucher type to embed. |
| Buyer contacted max 2×/week | Required | Shopee hard enforces; do not attempt override |
| Shop in good standing | Required | Confirm zero violation flags before campaign |

**Critical distinction:** The Hug tem (QR → Zalo identity capture) is a physical parcel insert, separate from Shopee Chat Broadcast. Do NOT describe the QR tem or Zalo OA capture in the broadcast message — that is the line between "service communication" and "off-platform solicitation."

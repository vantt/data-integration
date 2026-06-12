# Playbook: Daily · Customer Action Queue [Retail]

## Overview

- **Audience:** Customer Success, Sales
- **Goal:** Who to contact TODAY — daily outreach dispatch ranked by urgency and CLV
- **Collection:** `Marketing & Customers › 👥 Customer`
- **Cadence:** Daily (refreshes overnight)
- **Blueprint:** [`../blueprints/customer_daily_action_queue.md`](../blueprints/customer_daily_action_queue.md)

## Data Lineage

- **Core Model:** `mart_customer_action_queue` — daily snapshot, `action_type IS NOT NULL`
- **Watchlist Models:** `dim_customers` (VIP/At-Risk/Churned/Cancel all-time); `mart_customer_action_queue` (Reactivation Mine)
- **Scope:** Retail only (`scope_retail`); `customer_type = 'RETAIL'`

## Filters

- **Action Type:** CALL_NOW / REORDER_NUDGE / REORDER_PREEMPT / WIN_BACK / SECOND_ORDER / HIGH_CANCEL_RISK
- **Value Group:** VIP / GOLD / SILVER / BRONZE
- **Contactable:** default `true` — phone number present; no Zalo OA fallback (phone-only channel)
- **Next Purchase Signal:** OVERDUE / DUE_SOON / ON_TRACK

## Action Types

| Type | Meaning | Owner | Note |
|:---|:---|:---|:---|
| `CALL_NOW` | VIP/Gold/Silver at-risk — highest priority | CS Lead | Silver included (expanded from VIP/Gold only) |
| `REORDER_NUDGE` | Overdue reorder cycle | CS / Sales | Past expected repurchase window |
| `REORDER_PREEMPT` | DUE_SOON preempt — approaching cycle deadline | CS / Sales | New; triggers before customer goes OVERDUE |
| `WIN_BACK` | Churned customer — needs special offer | CS | recency > 90 days |
| `SECOND_ORDER` | 1-time buyer, 15-45 days no repeat | Sales | Convert one-time to repeat |
| `HIGH_CANCEL_RISK` | Cancel rate > 50% — confirm order proactively | CS | Proactive call before cancellation |

**Margin gate:** Queue table shows `is_margin_negative` flag. Avoid high-touch outreach on negative-margin customers — deprioritize, do not remove from queue entirely.

**Contactable constraint:** `is_contactable = true` means phone number on file. No Zalo OA integration; phone call / SMS only.

## Reading Flow

### Tab 1: 🎯 Hành động hôm nay

1. Check **queue date scalar** (top) — confirms snapshot is fresh and generated time.
2. Scan **6 action type counters** (CALL_NOW, REORDER_NUDGE, REORDER_PREEMPT, WIN_BACK, SECOND_ORDER, HIGH_CANCEL_RISK) — identify largest bucket.
3. Review **contactable scalars** — customers with phone who are OVERDUE/DUE_SOON; LTV at stake; total value at stake.
4. Work down the **outreach queue table** top-to-bottom (sorted `priority_rank → lifetime_value DESC`, max 500 rows). Check `Âm biên` flag before calling.
5. Use **Mã KH** link → detailView for full customer history before calling.
6. Review **value/count bar charts** — prioritize action buckets with most VND at risk.
7. Check **Upcoming Predicted Purchases** scalars — customers predicted to buy this week / this month (pipeline visibility).

### Tab 2: 👀 Watchlists

1. **VIP Watchlist** — top 50 VIP customers sorted by recency DESC; red rows = inactive > 60 days, call immediately.
2. **At-Risk Reactivation Priority** — all At-Risk customers sorted by LTV DESC; purple highlight = LTV ≥ 5M.
3. **Churned High-Value** — churned 91-180 days with LTV ≥ 1M; recovery campaign candidates.
4. **High Cancel Rate** — stacked bar by cancel rate band × segment; flag accounts > 50% for proactive confirmation.
5. **Next Purchase Signal Breakdown** — OVERDUE/DUE_SOON/ON_TRACK count by segment; identify urgency across base.
6. **Reactivation Mine (SILVER/GOLD/VIP)** — At-Risk and Churned high-tier by tier × status with phone count and contrib. margin.

## Visualizations

| Card | Type | Source |
|:---|:---|:---|
| Queue date scalar | Scalar | `mart_customer_action_queue` |
| CALL_NOW count | Scalar | action_type = 'CALL_NOW' |
| REORDER_NUDGE count | Scalar | action_type = 'REORDER_NUDGE' |
| REORDER_PREEMPT count | Scalar | action_type = 'REORDER_PREEMPT' |
| WIN_BACK count | Scalar | action_type = 'WIN_BACK' |
| SECOND_ORDER count | Scalar | action_type = 'SECOND_ORDER' |
| HIGH_CANCEL_RISK count | Scalar | action_type = 'HIGH_CANCEL_RISK' |
| Contactable Due/Overdue count | Scalar | `is_contactable=true`, signal IN (OVERDUE, DUE_SOON) |
| LTV at Stake (Contactable) | Scalar | SUM(lifetime_value) contactable queue |
| Value at Stake (Contactable) | Scalar | SUM(value_at_stake) contactable queue |
| Queue table | Table | Top 500; priority_rank → CLV DESC; margin flag; Mã KH → detailView |
| Value at stake by action | Horizontal bar | VND per action type |
| Count by action | Horizontal bar | Headcount per action type |
| Upcoming Purchases — This Week | Scalar | `dim_customers`, predicted_next_purchase_date +7d |
| Upcoming Purchases — This Month | Scalar | `dim_customers`, predicted_next_purchase_date +30d |
| VIP Watchlist | Table | `dim_customers`, value_group = VIP, recency heat |
| At-Risk Priority | Table | `dim_customers`, customer_status = At Risk, LTV DESC |
| Churned High-Value | Table | `dim_customers`, churned 91-180d, LTV ≥ 1M |
| High Cancel Rate | Stacked bar | `dim_customers`, cancel_rate bands × segment |
| Next Purchase Signal Breakdown | Table | `dim_customers`, OVERDUE/DUE_SOON/ON_TRACK × segment |
| Reactivation Mine | Table | `mart_customer_action_queue`, SILVER/GOLD/VIP At-Risk + Churned |

## Action Triggers

| Signal | Action |
|:---|:---|
| CALL_NOW > 0 | Call VIP/Gold/Silver before 10am |
| REORDER_PREEMPT > 0 | Send proactive reorder reminder (phone/SMS) |
| WIN_BACK + REORDER_NUDGE > 50 | Batch SMS campaign |
| HIGH_CANCEL_RISK > 5 | Proactive order confirmation calls |
| VIP Watchlist row red (> 60d inactive) | Escalate to CS Lead immediately |
| Value at Stake > 50M | Escalate to Sales Lead |

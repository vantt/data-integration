# Playbook: Customer Action Queue [Retail]

## Overview

- **Audience:** Customer Success, Sales
- **Goal:** Prioritize daily outreach — ranked list of retail customers needing contact today, ordered by urgency and CLV.
- **Collection:** `Marketing & Customers`
- **Blueprint:** [`blueprints/customer_action_queue.md`](../blueprints/customer_action_queue.md)

## Data Lineage

- **Core Model:** `mart_customer_action_queue` — daily snapshot, refreshes overnight
- **Scope:** Retail only (`scope_retail`); action_type IS NOT NULL

## Filters

- **Action Type:** CALL_NOW / REORDER_NUDGE / WIN_BACK / SECOND_ORDER / HIGH_CANCEL_RISK
- **Value Group:** VIP / GOLD / SILVER / BRONZE

## Action Types

| Type | Meaning | Who |
|:---|:---|:---|
| `CALL_NOW` | VIP/Gold at-risk — highest priority | CS Lead |
| `REORDER_NUDGE` | Overdue reorder cycle | CS / Sales |
| `WIN_BACK` | Churned customer — needs special offer | CS |
| `SECOND_ORDER` | 1-time buyer, 15-45 days no repeat | Sales |
| `HIGH_CANCEL_RISK` | Cancel rate > 50% — confirm order proactively | CS |

## Reading Flow

1. Check **queue date** (top scalar) — confirms snapshot is fresh.
2. Scan **5 action type counters** — identify which bucket is largest today.
3. Review **Value at Stake** bar — prioritize buckets with most VND at risk.
4. Work down the **outreach list** top-to-bottom (sorted by priority_rank → CLV).
5. Use **Mã KH** link → detailView for full customer history before calling.

## Visualizations

| Card | Type | Notes |
|:---|:---|:---|
| Queue date scalar | Scalar | Shows snapshot date + generated time |
| CALL_NOW count | Scalar | VIP/Gold at-risk |
| REORDER_NUDGE count | Scalar | Overdue reorder |
| WIN_BACK count | Scalar | Churned |
| SECOND_ORDER count | Scalar | Push 2nd order |
| HIGH_CANCEL_RISK count | Scalar | Cancel risk |
| Value at stake by action | Horizontal Bar | VND per action type |
| Customer count by action | Horizontal Bar | Headcount per action type |
| Outreach list table | Table | Top 500, sorted priority → CLV DESC; Mã KH links to detailView |

## Action Triggers

| Signal | Action |
|:---|:---|
| CALL_NOW > 0 | Call VIP/Gold before 10am |
| REORDER_NUDGE + WIN_BACK > 50 | Batch SMS campaign |
| HIGH_CANCEL_RISK > 5 | Proactive order confirmation calls |
| Value at stake > 50M | Escalate to Sales Lead |

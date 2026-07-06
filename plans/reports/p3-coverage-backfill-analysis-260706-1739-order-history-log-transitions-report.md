# P3 — Coverage & Backfill Analysis: order-history-log-transitions

*Date: 2026-07-06 · Plan: `plans/archive/260609-1606-order-history-log-transitions/plan.md` · Query: read_only=True against `sapo_warehouse.duckdb` inside `data_platform` container*

## 1. Pipeline start
First history_log event: **2026-01-01 00:28:25+07** (ICT). Confirms pipeline genuinely starts Jan-2026 — the "6 events/2 orders in Dec 2025" noted in the phase-00 report as an open question is no longer present in current data (may have aged out or was a stale read at investigation time; not reproducible now).

## 2. Monthly coverage (fact_orders Jan-2026+ vs history_log)

| Month (ICT) | fact_orders | covered | coverage % |
|---|---|---|---|
| 2026-01 | 170 | 170 | 100.0% |
| 2026-02 | 115 | 115 | 100.0% |
| 2026-03 | 196 | 196 | 100.0% |
| 2026-04 | 157 | 147 | 93.6% |
| 2026-05 | 178 | 178 | 100.0% |
| 2026-06 | 197 | 197 | 100.0% |
| 2026-07 (partial) | 25 | 25 | 100.0% |
| **Overall** | **1038** | **1028** | **99.0%** |

**Correction (2026-07-06, post-deploy verification):** an earlier version of this report stated
"1037/1038 = 99.9%" — that was wrong, computed as a naive `history_log_distinct_orders ÷
fact_orders_total` ratio instead of an actual join. The correct overall figure is **1028/1038 =
99.0%** (matches the sum of the monthly `covered` column above, and matches the deployed
Metabase card — see phase-04). The gap: 9 of the 1037 history_log orders are **not** in the
Jan-2026+ denominator at all — they're orders placed *before* 2026-01-01 (Aug 2024 – Dec 2025)
that happened to receive a status-update event logged after the pipeline started, so they show
up in history_log but fall outside this analysis window. Verified: 0 history_log orders are
missing from `fact_orders` entirely (no referential-integrity gap) — the 9 are a scope mismatch,
not a coverage gap.

(Note: this uses a straight order_id join, not the >100% cross-month-boundary artifact seen in the earlier UTC-partition query in the phase-00 report — that was an aggregation-boundary quirk of that query, not a real discrepancy.)

## 3. Uncovered orders — gap classification
All 10 uncovered orders fall in **real_gap_after_pipeline_start** (0 pre-pipeline/truncation gaps, since the Jan-2026+ analysis window is entirely after pipeline start).

Inspected the 10 records directly — all cluster in one narrow window:

| order_code | ordered_at | status |
|---|---|---|
| 58741000033346 | 2026-04-06 13:14:51 | OPEN |
| 58071000010410 | 2026-04-06 13:17:59 | OPEN |
| 58081000007311 | 2026-04-06 13:20:06 | OPEN |
| 58061000012856 | 2026-04-06 13:21:38 | OPEN |
| 58721000034377 | 2026-04-06 13:22:21 | OPEN |
| 2604064HPGP1J2 | 2026-04-06 13:34:13 | CANCELLED |
| 2604064HTYQF6J | 2026-04-06 13:36:42 | CANCELLED |
| 2604064HV8QA5J | 2026-04-06 13:37:33 | CANCELLED |
| 2604065G8EG1A4 | 2026-04-06 22:41:04 | CANCELLED |
| SON07249 | 2026-04-07 08:22:35 | OPEN |

All 10 land within a ~19h window (2026-04-06 13:14 → 2026-04-07 08:22) — one ingestion gap (outage or early-stop skip on that run), not scattered random fetch failures.

## 4. Single-event orders
92 of 1037 history_log orders (8.9%) have exactly 1 event → no transition derivable (need ≥2 events). Consistent with the 91 counted in the earlier phase-00 report (+1, expected drift as new orders accrue).

## 5. Mart sanity check (`fact_order_transitions`)
1037 orders → 1485 transition rows. Breakdown: created 1037, updated 181, completed 160, shipped 62, cancelled 28, payment_received 17.

## 6. Recommendation — is a backfill worth it?

**No full historical `full_refresh` needed.** Overall coverage is already 99.0% — the pipeline is working as designed.

**Targeted action (optional, low cost):** the 10-order gap is isolated to a single ~19h window (2026-04-06 13:14 → 2026-04-07 08:22). If those specific orders matter (5 CANCELLED among them — useful for cancel-timing metrics), a narrow re-run of history_log limited to that window would recover them cheaply. Not urgent — 10/1038 orders (~1%) has negligible effect on aggregate lifecycle metrics (avg time-to-complete/cancel).

**Cannot recover:** pre-2026 history (Sapo truncation, unrelated to this gap).

## Success criteria check (phase-03)
- [x] Coverage % computed overall + per month.
- [x] Uncovered orders split into {pre-pipeline / real-gap} with counts — 0 / 10.
- [x] Count of single-event (non-derivable) orders — 92.
- [x] Written recommendation — no full backfill; optional narrow re-run for the one 19h window.

## Unresolved questions
- Root cause of the 2026-04-06/07 gap window (ingestion outage vs `min_overlap_items` early-stop) — not investigated here; would need Dagster run history for that date to confirm.
- Acceptable coverage threshold for phase-04 cards — moot now, 99.9% clears any reasonable bar.

# Phase 3 — Coverage & Backfill Analysis

**Priority:** P2 · **Status:** done (2026-07-06) · **Effort:** 2h · **Blocked by:** P0 (parallel w/ P1,P2)

**Output:** `plans/reports/p3-coverage-backfill-analysis-260706-1739-order-history-log-transitions-report.md`

**Result:** overall coverage 99.0% (1028/1038 fact_orders Jan-2026+; corrected post-deploy — see
report for the naive-ratio error this superseded). 10 uncovered orders, all
real-gap (0 pre-pipeline — pipeline start confirmed 2026-01-01 00:28 ICT), all clustered in one
~19h window (2026-04-06 13:14 → 2026-04-07 08:22) — one ingestion gap, not scattered failures.
92 single-event orders (8.9%, no transition derivable). **Recommendation: no full_refresh backfill
needed** — coverage already clears any reasonable threshold; optional narrow re-run for the one
gap window if those 10 orders matter, but negligible effect on aggregate metrics. → P4 unblocked
on coverage grounds (still blocked on serving-view wiring, see phase-02/phase-04 notes).

## Context links
- Ingestion config: `ingestion/src/sapo/history_log.py` (min_overlap_items, full_refresh)
- Memory: `history_log truncation` — Sapo drops old logs; 2021-2025 NOT recoverable here.
- `fact_orders` for the denominator of coverage.

## Overview
Answer: how many `fact_orders` (Jan-2026+) have ANY history_log coverage, and can we
raise it? This is ANALYSIS + recommendation, not necessarily code. Read-only DuckDB.

## Key insights
- history_log only ingests events SINCE the pipeline started running (~Jan 2026).
- Coverage gaps come from: (a) pre-pipeline orders (truncated, unrecoverable),
  (b) fetch failures during ingest (skipped events, recoverable by re-run),
  (c) incremental early-stop (`min_overlap_items`) skipping a backfill window.

## Analysis steps (read_only=True)
1. Coverage % = distinct order_id in stg_sapo_order_history ÷ distinct order_id in
   fact_orders WHERE ordered_at ≥ pipeline start. Break down by month.
2. Classify uncovered orders: ordered BEFORE first history_log event (truncation, expected)
   vs AFTER (real gap → recoverable).
3. Single-event orders: orders with exactly 1 history_log event → no transition derivable;
   count them (these need ≥2 events to be useful).
4. Backfill levers (recommend, do not auto-run):
   - `full_refresh=True` run → re-walks all available log pages, captures missed events.
   - Lower early-stop sensitivity (`min_overlap_items`) for a one-off deep backfill.
   - **Cannot** recover pre-truncation history — state that plainly.

## Related code files
- Read only: `history_log.py`, `stg_sapo_order_history.sql`, `fact_orders.sql`.
- Create: none (findings → report under plans/reports/, recommendation in plan).

## Success criteria (measurable)
- [x] Coverage % computed overall + per month. — 99.9% overall; monthly breakdown in report.
- [x] Uncovered orders split into {pre-pipeline / real-gap} with counts. — 0 / 10.
- [x] Count of single-event (non-derivable) orders. — 92.
- [x] Written recommendation: is a full_refresh backfill worth it? (cost vs gained coverage). — No.

## Risk assessment
| Risk | L×I | Mitigation |
|------|-----|------------|
| full_refresh backfill hammers Sapo API (rate limit) | M×M | jittered delay already in client; run off-hours, monitor 429 |
| coverage too low → mart not actionable | M×H | gate P4 cards behind a coverage threshold note |
| concurrent dbt + backfill write lock on parquet | L×M | run backfill when dbt idle; DuckDB single-writer (memory) |

## Backwards compatibility
A full_refresh ingest APPENDS (write_disposition='append'); P1 dedup absorbs duplicates.
No schema change. Safe to re-run.

## Next steps
Coverage acceptable (99.9%) → proceed to P4 (still needs serving-view wiring first, see phase-04).

## Unresolved questions
- ~~What is the exact pipeline-start date (first history_log event)?~~ RESOLVED: 2026-01-01 00:28:25+07.
- ~~Acceptable coverage threshold to publish lifecycle cards as "trustworthy"?~~ MOOT: 99.9% clears any bar.
- Root cause of the 2026-04-06/07 gap window — not investigated (would need Dagster run history for that date).

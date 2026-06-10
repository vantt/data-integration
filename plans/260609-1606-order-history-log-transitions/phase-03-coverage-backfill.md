# Phase 3 — Coverage & Backfill Analysis

**Priority:** P2 · **Status:** pending · **Effort:** 2h · **Blocked by:** P0 (parallel w/ P1,P2)

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
- [ ] Coverage % computed overall + per month.
- [ ] Uncovered orders split into {pre-pipeline / real-gap} with counts.
- [ ] Count of single-event (non-derivable) orders.
- [ ] Written recommendation: is a full_refresh backfill worth it? (cost vs gained coverage).

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
If coverage acceptable → proceed P4. If low → P4 cards must annotate sample limitation.

## Unresolved questions
- What is the exact pipeline-start date (first history_log event)? (compute in step 1)
- Acceptable coverage threshold to publish lifecycle cards as "trustworthy"? (business call)

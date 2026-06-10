# Phase 0 — Investigate

**Priority:** P1 (blocks P1, P3) · **Status:** pending · **Effort:** 2h

## Context links
- Raw glob: `sapo_raw/order/ingest_method=history_log/**/*.parquet`
- Ingestion: `ingestion/src/sapo/history_log.py`
- Source def: `transformation/models/sources.yml` (sapo_v2_raw.order globs ALL methods)

## Overview
Confirm what is recoverable BEFORE writing models. Three sub-investigations:
raw parquet schema, Sapo API log granularity, coverage gap vs `fact_orders`.

## Key insights (from pre-investigation)
- Source `sapo_v2_raw.order` already reads history_log partition (no source change needed).
- Envelope cols: `entity_id` (order_id), `event_type` (add/update), `event_timestamp`
  (occurAt), `payload` (full order JSON), `payload_hash` (md5), `sync_metadata`.
- `sync_metadata.actor_name` + `.description` carry actor + HTML log description (UNUSED today).
- 4,053 rows, 893 orders, Jan 2026→now. Duplicate (ts+hash) events exist (dlt double-ingest).

## Investigation steps (read-only, DuckDB read_only=True ALWAYS)
1. **Raw schema** — query parquet directly:
   - row count, distinct orders, distinct payload_hash per order distribution.
   - `payload.status` value set; events-per-order histogram.
   - duplicate detection: `COUNT(*)` grouped by `entity_id, event_timestamp, payload_hash`.
   - confirm `sync_metadata.description` distinct values (are they truly generic only?).
2. **Sapo API log fields** — read `settings/get_logs` response shape in `history_log.py`
   (lines 314-446). Confirm RAW log item fields NOT persisted: `actionName`, `actorName`,
   `description`, `uri`, `id`. Decide: does raw log offer finer action than add/update?
   - If finer action text exists in `description` (e.g. status-change phrases), capturing
     it would beat status-diffing. Probe a sample via the live endpoint if creds available;
     else rely on persisted `sync_metadata.description`.
3. **Coverage gap** — `SELECT COUNT(DISTINCT order_id)` in `fact_orders` WHERE ordered ≥ Jan 2026
   vs distinct history_log orders. Compute coverage %. Identify which orders LACK history.

## Related code files
- Read only: `ingestion/src/sapo/history_log.py`, `transformation/models/sources.yml`,
  `transformation/models/staging/src_sapo_orders_v2.sql`, `fact_orders.sql`.
- Create: none (analysis only — output findings into phase-01/03 as confirmed facts).

## Success criteria (measurable)
- [ ] Documented: exact `payload.status` value domain (e.g. draft/finalized/completed/cancelled).
- [ ] Documented: duplicate-event rate (rows that share entity_id+ts+hash).
- [ ] Decided: is `sync_metadata.description` usable for action labels? (Y/N + evidence).
- [ ] Documented: coverage % of fact_orders Jan-2026+ orders present in history_log.

## Risk assessment
| Risk | L×I | Mitigation |
|------|-----|------------|
| description generic only → no extra signal | M×L | fall back to status-diff (plan baseline) |
| payload.status absent for some events | L×M | NULL-guard in P1; exclude from transitions |
| coverage <50% → mart misleading | M×H | surface coverage % on every card (P4) |

## Next steps
Feed confirmed status domain + dup rate into phase-01. Feed coverage method into phase-03.

## Unresolved questions
- Does live `get_logs.description` contain status-change phrasing per event? (needs creds probe)
- Are there statuses beyond the 4 observed (draft/finalized/completed/cancelled)?

---
title: "Ingestion Trust Engineering"
description: "Give the user visible, queryable confidence that every ingestion actually moved data — not just ran green."
status: in-progress
priority: P1
effort: ~22h
branch: main
tags: [dagster, dlt, duckdb, observability, reconciliation, lark]
created: 2026-04-15
---

## Problem

Many Dagster jobs run on schedule/sensors. Jobs exit green but data silently missing or partial (cursor bugs, auth expiry, pagination truncation, unconsumed file drops, schema drift). User wants **existence confirmation**, not latency guarantees. SLAs stay loose (12h) for now.

Dagster event-log is ephemeral → historical trust metrics MUST live in a dedicated DuckDB.

## Architecture (5 layers)

| # | Layer | Output | Status |
|---|-------|--------|--------|
| 0 | Ingestion-health writer + DB | `ingestion_health.duckdb` + `record_run()` | DONE — commit `bb5c965` |
| 1 | Metadata contract rollout | All ingestion assets call `_record_health` | DONE — commit `5801b31` |
| 2 | Asset-checks (Dagster-native) | `@asset_check` per ingestion asset, reads health DB | DONE — commit `97cee41` |
| 3 | Source↔Destination reconciliation | Daily `recon_<src>_daily` assets + drift metric | DONE — commit `957a599` |
| 4 | Morning Lark digest | 08:00 summary card — 24h volume, trend, drift, freshness | DONE — commit `5d171fe` |
| 5 | KPI-closure (revenue invariant) | DEFERRED — stub only | deferred |

## Dependency graph

```
Phase 0 (done)
   ↓
Phase 1 (metadata contract) ──────┐
   ↓                              ↓
Phase 2 (asset checks)      Phase 3 (recon)  ← gated by research/sapo-page-metadata-verification.md
   ↓                              ↓
        Phase 4 (Lark digest) — reads all above
                       ↓
             Phase 5 (stub, deferred)
```

Phase 1 is the unblocker. Phase 2 & 3 can run in parallel once Phase 1 lands. Phase 4 needs both.

## File-ownership map (parallel-safe)

| Phase | Owns | Reads |
|-------|------|-------|
| 1 | `orchestration/ops/dlt_metrics.py` (new), `orchestration/assets/sapo_assets.py`, `orchestration/assets/misa_amis_assets.py`, `orchestration/assets/shopee_assets.py`, `orchestration/assets/sheets_assets.py` | `ops/ingestion_health.py` |
| 2 | `orchestration/asset_checks/` (new dir), `orchestration/config/ingestion_sla.yaml` (new), `orchestration/definitions.py` (register) | health DB |
| 3 | `orchestration/assets/reconciliation.py` (new), `ingestion/src/sapo/api_count.py` (new, if API allows) | health DB, raw DBs |
| 4 | `orchestration/sensors/morning_digest.py` (new), `orchestration/definitions.py` (register) | health DB |
| 5 | stub file only | — |

No two phases touch the same file simultaneously.

## Phases

- [Phase 1 — Metadata contract rollout](./phase-01-metadata-contract.md)
- [Phase 2 — Asset checks](./phase-02-asset-checks.md)
- [Phase 3 — Source↔Destination reconciliation](./phase-03-reconciliation.md)
- [Phase 4 — Morning Lark digest](./phase-04-lark-digest.md)
- [Phase 5 — KPI closure (deferred stub)](./phase-05-kpi-closure.md)

## Research gate

- [research/sapo-page-metadata-verification.md](./research/sapo-page-metadata-verification.md) — blocks Phase 3 Sapo recon. Must complete first tick of Phase 3.

## Success criteria (whole initiative)

1. Every ingestion asset writes one row per run to `ingestion_health.duckdb`.
2. Every ingestion asset has at least one `@asset_check` gating freshness OR row-trend.
3. One SQL query against `ingestion_health.duckdb` answers "is every source healthy today?".
4. One Lark card lands at 08:00 daily, contains per-source verdict (OK/WARN/FAIL).
5. When something breaks silently (e.g. cursor frozen with rows=0 for 3 ticks), a WARN signal appears within 24h without the user looking.

## Rollback

Each phase is additive and read-only against existing ingestion code paths. Rollback = remove the new files + revert the small insertions in `sapo_assets.py` et al. Dropping `ingestion_health.duckdb` is safe (recreated lazily).

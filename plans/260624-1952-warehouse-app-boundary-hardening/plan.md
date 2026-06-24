# Warehouse ↔ App Boundary Hardening

**Created:** 2026-06-24 · **Branch:** main · **Status:** Planning

## Goal

Harden the contracts + resilience at the boundaries between the DuckDB warehouse
(foundation) and the apps on top (CRM, hug, Metabase, Evidence, Rill, DetailView)
**before** any physical service split. Keep warehouse-as-platform. De-risk the current
monolith; make every future split cheap. Build boundaries first, split last.

## Decisions (locked)

- **Scope:** Tier 1 (contracts) + Tier 2 (resilience) + Tier 3 *prep* (CRM service
  boundary DESIGN only — ADR + contract spec, NO code split).
- **Fail mode:** fail-loud + alert + stop sync (data correctness over availability).

## Key grounding (see research report)

- Research findings: `plans/reports/from-research-to-planner-boundary-hardening-findings-260624-1952-report.md`
- Corrections that reshaped the plan: `duckdb_reader.py` already fail-loud (real gap =
  alerting+observability); dbt contracts guard at parquet-write/Dagster (not consumer
  runtime); `exposures.yml` exists but Metabase-only; `build_standalone_export` is the
  snapshot basis but lacks `main_marts` aliases.

## Phases

| # | Phase | Tier | Status | Depends |
|---|-------|------|--------|---------|
| 01 | [dbt model contracts](phase-01-dbt-model-contracts.md) — pin versions, complete schema.yml+data_type for 6 consumed marts, override on_schema_change, enable `contract:enforced` (spike external/parquet first) | 1 | Pending | — |
| 02 | [consumer contract & exposures](phase-02-consumer-contract-exposures.md) — curated non-Metabase exposures file (CRM/hug/Evidence/Rill/DetailView), published mart→consumer contract doc | 1 | Pending | 01 |
| 03 | [CRM sync observability & alerting](phase-03-crm-sync-observability-alerting.md) — Lark alert on refresh failure, persisted `crm_etl_run` health record, digest surfacing, hug best-effort reclassification, tighten the one CatalogException skip | 2 | Pending | — |
| 04 | [serving snapshot isolation](phase-04-serving-snapshot-isolation.md) — extend `build_standalone_export` (main_marts aliases + version sidecar), repoint BI to snapshot → removes Metabase-holds-lock coupling | 2 | Pending | — |
| 05 | [durable serving-ready trigger](phase-05-durable-serving-ready-trigger.md) — `serving_version.json` marker, replace fire-and-forget with version-poll + durable ACK; CRM catch-up automatic | 2 | Pending | 04 |
| 06 | [CRM service-boundary ADR](phase-06-crm-service-boundary-adr.md) — ADR-015 + consumption contract spec + readiness checklist + split triggers (DESIGN ONLY) | 3-prep | Pending | 02,04,05 |

## Execution order

`01 → 02` (Tier 1) ‖ `03` (independent) ‖ `04 → 05` (Tier 2 serving). `06` last (design synthesis).
Phases 01, 03, 04 can start in parallel (different sub-projects, no file conflicts).

## Non-goals

- No physical service split / polyrepo. No DuckDB→server-DB migration. No new infra.
- No re-derivation of semantic concepts. No edits to auto-generated `exposures.yml`.

## Constraints

- Windows native + Docker Linux dual-runtime; forward-slash paths; `os.path.join`.
- DuckDB single-writer; serving assets carry `duckdb_lock`. Don't break `dbt_rw` limit=1.
- Code/migration names + comments: NO plan/phase/finding references (stable why only).

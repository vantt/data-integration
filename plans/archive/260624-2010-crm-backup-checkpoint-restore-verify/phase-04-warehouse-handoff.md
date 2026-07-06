---
phase: 4
title: Warehouse Handoff
status: completed
priority: P3
effort: 0.5d
dependencies:
  - 1
  - 2
  - 3
---

# Phase 4: Warehouse Handoff

## Overview
Capture what the CRM pilot proved, then **write a follow-up plan** for warehouse-pipeline DR (verified restore) — do NOT implement the warehouse here (YAGNI: detail it only after CRM validates the pattern). This phase is a lessons doc + a new plan stub.

## Requirements
- **Functional:** a short lessons-learned note from the CRM pilot; a new `plans/` plan for warehouse DR with the right source-of-truth analysis + DuckDB-specific consistency approach.
- **Non-functional:** reuse the CRM pattern (manifest-driven verify, ephemeral fresh-app boot, integrity + functional checks); be honest about where the warehouse differs.

## Architecture / key differences to encode in the follow-up plan
- **Source-of-truth vs regenerable (warehouse):**
  - **Irreplaceable:** the **raw Parquet data lake** (append-only; holds 2021-2025 Sapo history — see memory `project_sapo_history_log_truncation`), `dagster_home` instance state (`dagster.yaml`, schedules, storage), seeds.
  - **Regenerable:** `sapo_warehouse.duckdb` (dbt rebuilds it), serving `olap.duckdb` + standalone export + all marts (rebuildable from raw via `dbt run` + serving build).
  - **Implication:** warehouse "backup" centers on **raw parquet + dagster_home + seeds**; "restore" = restore those, then **re-run dbt + serving build** to reconstruct everything. Verifying = the rebuilt marts match expected (row counts / KPI invariants), not byte-identical DBs.
- **Consistency (DuckDB has no SQLite-style online backup):** options to evaluate in the follow-up — `EXPORT DATABASE`, file copy under the `duckdb_lock` (pause writers), or rely on the already-immutable parquet + a `dbt`-rebuild restore. Parquet-as-source-of-truth likely makes DuckDB-file consistency a non-issue.
- **Reuse from CRM:** manifest+checksum verification, ephemeral isolated restore env, integrity + functional (a serving query / KPI invariant) checks, clean exit codes for Dagster.
- **Existing assets to fold in:** `scripts/backup/backup.sh` (already backs up data_lake/dagster_home/crm_data), `system_backup.py` Dagster op, lessons L50/L51/L56/L58/L68; coordinate with the C1 backup-security item in `260624-1958-pipeline-hardening-followups`.

## Related Code Files
- Create: `plans/reports/from-crm-dr-pilot-lessons-{date}-report.md` (lessons)
- Create: a new plan dir `plans/{date}-warehouse-pipeline-dr-verified-restore/` (via `ck plan create`) — stub + phases, not implemented here

## Implementation Steps
1. After Phases 1-3 are done, write the lessons report (what worked, surprises, what to change for the warehouse).
2. `ck plan create` the warehouse-DR plan; seed it with the source-of-truth analysis above + a parquet-first restore strategy.
3. **Carry forward the CRM red-team hardening** (these generalize): backup is a GATE that compares against the live source (not a blind dump); content checksums not just row counts; restore-verify runs **isolated** from prod (no prod mounts/network) with image-digest pinning; the drill must test the **cross-version / rebuild-from-source** recovery path (warehouse: restore raw parquet → `dbt run` → verify marts), not byte-identical files; state **RPO** + add an offsite copy + backup-failure alerting. See `plans/.../reports/from-redteam-*-crm-backup-260624-2010-report.md`.
4. Cross-link both plans (`blocks`/`blockedBy` as appropriate).

## Success Criteria — ✅ DONE (2026-06-24)
- [x] Lessons report written from the actual CRM pilot (`plans/reports/from-crm-dr-pilot-lessons-260624-2010-report.md`).
- [x] Warehouse-DR follow-up plan exists with source-of-truth analysis + parquet-first strategy (`plans/260624-2010-warehouse-pipeline-dr-verified-restore/`).
- [x] No warehouse implementation done in this plan (scope held).

## Risk Assessment
- **Over-engineering early** → keep this phase to lessons + plan; resist building warehouse DR before CRM proves the pattern.
- **Wrong source-of-truth assumption** → the follow-up plan must confirm parquet immutability + that dbt fully rebuilds marts before treating DuckDB files as disposable.

---
title: "Warehouse Pipeline DR — Verified Restore (parquet-first)"
description: ""
status: pending
priority: P2
created: 2026-06-24
---

# Warehouse Pipeline DR — Verified Restore (parquet-first)

## Overview

**STUB** — generalizes the proven CRM DR pilot (`260624-2010-crm-backup-checkpoint-restore-verify`, Phases 1-3 done) to the warehouse. Detail when picked up. Lessons + rationale: `plans/reports/from-crm-dr-pilot-lessons-260624-2010-report.md`.

**Core strategy — parquet-first (DuckDB is NOT byte-snapshotted):**
- **Source of truth = raw Parquet lake** (append-only; holds 2021-2025 Sapo history) + `dagster_home` state + seeds. **Regenerable** = `sapo_warehouse.duckdb`, serving `olap.duckdb`, standalone export, all marts (dbt rebuilds them).
- **Backup** = the raw parquet + dagster_home + seeds (with a manifest/checksum gate like CRM). DuckDB has no SQLite-style online backup → don't try to snapshot a live DuckDB.
- **Restore-verify** = restore raw → `dbt run` + serving build in an **isolated** env → verify the **rebuilt marts** (row counts / KPI invariants / a serving query), NOT byte-identical files. Reuse the CRM pattern: manifest gate, isolation, prod-untouched assertion, negative tests, clean exit codes.

**Carry-forward from CRM red-team:** backup-as-a-gate (vs blind dump) · content not just counts · hard prod-isolation · cross-version/rebuild path is the real recovery case · offsite + RPO + backup-age alerting.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Parquet+State Backup](./phase-01-parquet-state-backup.md) | Pending |
| 2 | [Rebuild-Restore Verify](./phase-02-rebuild-restore-verify.md) | Pending |
| 3 | [DR Runbook](./phase-03-dr-runbook.md) | Pending |

## Dependencies

- **blockedBy:** [260624-2010-crm-backup-checkpoint-restore-verify](../260624-2010-crm-backup-checkpoint-restore-verify/plan.md) — proves the pattern this generalizes.
- **Related:** [260624-1958-pipeline-hardening-followups](../260624-1958-pipeline-hardening-followups/plan.md) — backup security (C1) + Cloudflare rotation.

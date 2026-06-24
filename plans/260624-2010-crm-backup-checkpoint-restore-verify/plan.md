---
title: "CRM Backup-Checkpoint + Verified Restore (DR pilot)"
description: ""
status: pending
priority: P2
created: 2026-06-24
---

# CRM Backup-Checkpoint + Verified Restore (DR pilot)

## Overview

Build a **CRM-owned backup-checkpoint** capability whose success is measured by a **verified restore (DR drill)**: a backup is only "good" if it can bootstrap a *fresh, fully-working CRM* with *provably-correct data*. The restore-verify drill — not the backup files — is the real deliverable. CRM is the **pilot**; lessons feed a later warehouse-pipeline DR plan (Phase 4 handoff).

**What CRM persists** (verified): both SQLite DBs live in Docker named volume `crm_data:/data`.
- `crm.db` — **source of truth** (schema via `crm/migrations/*.up.sql`; parties/tags/segments/tasks/campaigns/hug-identity/voucher/consent/app-users). Irreplaceable.
- `cache.db` — reverse-ETL snapshot from warehouse (regenerable via `reverse_etl`). Included in backup for **self-contained restore** (no warehouse needed), per scope decision.

**Existing gap:** `scripts/backup/{backup.sh,backup.ps1}` already copy the `crm_data` volume **raw** (WAL-unsafe — L56/L68) and there is **zero restore verification**. This plan replaces that with a consistent SQLite snapshot + a fresh-app restore drill.

**Scope decisions (user, 2026-06-24):** back up `crm.db`+`cache.db` · **standalone CRM mechanism** (not folded into `backup.sh`) written as **callable function + CLI** so it can wire into Dagster later · **on-demand** backup + restore-verify scripts + a manual-recovery runbook (schedule later) · backup **security/encryption is OUT of scope** (handled elsewhere).

**Non-goals:** scheduling/automation wiring (design for it, don't build it) · backup encryption/PII-sanitization/C1 secret fix (see [pipeline-hardening-followups](../260624-1958-pipeline-hardening-followups/plan.md)) · warehouse implementation (Phase 4 only writes the follow-up plan).

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Backup Mechanism](./phase-01-backup-mechanism.md) | Pending |
| 2 | [Restore-Verify Drill](./phase-02-restore-verify-drill.md) | Pending |
| 3 | [DR Runbook](./phase-03-dr-runbook.md) | Pending |
| 4 | [Warehouse Handoff](./phase-04-warehouse-handoff.md) | Pending |

## Dependencies

- **Related (non-blocking):** [260624-1958-pipeline-hardening-followups](../260624-1958-pipeline-hardening-followups/plan.md) owns backup **security** (C1 secret-sanitize, encryption). This plan deliberately ignores backup security; coordinate so the two don't conflict on `backup.sh`/backup layout.
- **Phase 4 emits** a new follow-up plan: warehouse-pipeline DR (DuckDB warehouse + raw parquet lake + dagster_home), generalizing the pattern proven here.

## Key conventions baked in (hardened by red-team 2026-06-24)
- **Consistency:** `PRAGMA wal_checkpoint(TRUNCATE)` + `integrity_check` on the **live** source BEFORE `sqlite3.Connection.backup()`; never raw copy of a live WAL DB (L56/L68).
- **Backup is a GATE, not a dump:** capture **live source** per-table row counts + content checksums at backup time and assert the snapshot matches (delta==0) — else the backup FAILS. (Closes red-team H1: a manifest computed only from the backup can't detect a backup that silently lost data.)
- **Manifest = fidelity truth:** per-DB sha256, per-table **row counts AND content checksums** (`hash(group_concat(pk||updated_at ORDER BY pk))`), migration head, `integrity_check`, image digest, `source_*` counts. Row-count+sha alone miss value mutation (H5).
- **Isolation (hard-asserted):** restore-verify runs a throwaway container with a **distinct name/port/temp volume**, `docker rm -f` first, **NO `crm_data` mount, NO `caddy_net`, NO Caddy label, NO prod port**; pins the **same image digest** prod runs; asserts prod `crm.db` unchanged before/after.
- **Cross-version restore is first-class:** the drill MUST also test "backup at head N → current code head N+k" (forward-migrate), since that's the real recovery case; sha-match only applies to same-version restores.
- **Rotation/retention:** keep-N + always-run cleanup (L50); 2× disk pre-flight (L58); backup dest + drill temp data on **Docker named volumes** (WSL2 — avoids Windows Defender/dllhost locking `.db` files mid-write).
- **Dagster wiring is NOT free (corrected):** backup runs *inside* the `crm` container (`docker exec`), but `data_platform` (Dagster) has **no Docker socket**. Future scheduling needs ONE of: (a) expose backup as a CRM HTTP admin endpoint Dagster calls, (b) give the orchestrator a Docker socket (security trade-off), or (c) a host cron. Phase 1 keeps the logic callable; the wiring is a real decision, not a no-op.
- **Reconcile existing backups:** `backup.sh`/`backup.ps1` already raw-copy `crm_data` (WAL-unsafe). Phase 1 **disables that crm_data leg** and declares this tool authoritative — avoid 3 competing crm backup formats.
- **Honest DR scope:** backups are **local-only** = NOT real DR against host loss. Runbook states this + names a minimal offsite path. Add **failure alerting** (Lark) — silent backup failure is the zombie-run lesson repeating.

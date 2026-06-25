---
phase: 1
title: Backup Mechanism
status: completed
priority: P1
effort: 1d
dependencies: []
---

# Phase 1: Backup Mechanism

## Overview
A standalone, CRM-owned tool that takes a **consistent point-in-time snapshot** of `crm.db` + `cache.db` and writes a `manifest.json` capturing the "expected truth" (checksums, row counts, migration head) that Phase 2 verifies against.

## Requirements
- **Functional:** consistent snapshot of both SQLite DBs from the live `crm_data` volume (no app downtime); timestamped backup dir; `manifest.json`; keep-N rotation; clean exit code + summary.
- **Non-functional:** WAL-safe (online-backup API, not `cp`); idempotent + re-runnable; pure-callable + CLI (future Dagster op); disk pre-flight; never corrupt the live DB.

## Architecture
- **Module:** `crm/ops/backup_crm.py` — `def backup_crm(data_dir: str, dest_root: str, keep: int) -> BackupResult` + `python -m crm.ops.backup_crm` CLI. Python (matches CRM stack; trivially importable by a future Dagster op).
- **Consistency:** open each source DB read-only via `sqlite3.connect("file:{path}?mode=ro", uri=True)`, copy with `src.backup(dst)` (SQLite online-backup API → page-consistent even under concurrent writes / WAL). NEVER `cp`/`tar` the live `.db` (torn WAL — L56/L68).
- **Run context:** executes **inside the live `crm` container** (`docker exec crm python -m crm.ops.backup_crm …`) so SQLite owns its locking/WAL — avoids the read-only-mount WAL/shm problem a sidecar hits. Needs a writable backup dest mount.
- **Backup dest:** a **Docker named volume `crm_backups`** mounted into `crm` as `/backups` (NOT a host bind — host `.db` files get Defender/dllhost-locked mid-write). Layout inside: `/backups/{YYYYMMDD-HHMMSS}/{crm.db, cache.db, manifest.json}`. A separate **export step** (`docker cp` / tar) copies a chosen snapshot out to host/offsite when needed (runbook Phase 3).
- **Manifest** (`manifest.json`): `created_at`, `sqlite_version`, and per-DB: `sha256` of the snapshot file, `file_size`, `integrity_check` result (`PRAGMA integrity_check`), `migration_head` (max applied version from the migrations/`schema_migrations` table), `tables: {name: row_count}` for every table.
- **Rotation:** keep newest `CRM_BACKUP_KEEP` (default 7) timestamped dirs; cleanup registered to always run (EXIT path) so a failed/partial backup dir is removed and rotation still fires (L50). Disk pre-flight: abort cleanly if free space < snapshot size × safety factor (L58).

## Related Code Files
- Create: `crm/ops/__init__.py`, `crm/ops/backup_crm.py`
- Modify: `docker-compose.yml` (declare named volume `crm_backups` + mount `- crm_backups:/backups` on the `crm` service)
- Modify: `scripts/backup/backup.sh` (remove `crm_data` from the volume-copy loop ~line 152) + `scripts/backup/backup.ps1` (remove Step 3 crm_data copy) — deprecate the raw/WAL-unsafe crm backup legs
- Reference (read): `crm/entrypoint.sh`, `crm/src/adapters/outbound/sqlite/migrations.py` (migration-head/`schema_migrations` table name), `scripts/backup/backup.sh` (rotation/disk-check patterns to reuse), `orchestration/notifications/lark_client.py` (failure-alert pattern)

## Implementation Steps
1. Read `migrations.py` for the applied-migrations table name + current head.
2. Write `crm/ops/backup_crm.py` with the **gate** ordering: (a) `wal_checkpoint(TRUNCATE)` + `integrity_check` on the LIVE source; (b) read live per-table row counts + content checksums; (c) `src.backup(dst)` into the timestamped dir; (d) read snapshot counts/checksums + sha256; (e) **assert snapshot == source (delta 0)** or FAIL. Record `image_digest`, `source_*`, `snapshot_*`, per-DB `partial` flag in `manifest.json`.
3. Add 2× disk pre-flight + keep-N rotation with always-run cleanup (mirror `backup.sh` trap; preserve a completed `crm.db` even if `cache.db` fails). Add Lark alert on failure.
4. Declare named volume `crm_backups` + mount it on `crm` in `docker-compose.yml`; recreate `crm`. Remove the `crm_data` legs from `backup.sh` + `backup.ps1`.
5. Run: `docker exec crm python -m crm.ops.backup_crm --data-dir /data --dest /backups --keep 7`.
6. Inspect `manifest.json`; confirm `source_* == snapshot_*`, both `integrity_check=ok`, image digest + content checksums present.

## Success Criteria — ✅ DONE (verified on live prod 2026-06-24)
- [x] Backup produces `crm.db`, `cache.db`, `manifest.json` in a timestamped dir on the `crm_backups` named volume.
- [x] **Gate:** backup FAILS if snapshot ≠ live source (delta≠0); on success the manifest records matching `source`/`snapshot` profiles per DB.
- [x] Both DBs `integrity_check = ok`; manifest has per-DB sha256 + content checksums + migration head. _(image_digest field present but `null` until `CRM_IMAGE_DIGEST` set at backup — polish backlog.)_
- [x] Rotation keep-N; a `cache.db` failure preserves a completed `crm.db` (`partial=true`).
- [x] No impact on the live CRM (ran against 7572 parties, zero downtime). _(Lark alert is a best-effort hook, not yet exercised by a real failure.)_
- [x] `crm_data` legs removed from `backup.sh` + `backup.ps1`.
- [x] Module import-callable + also exposed via `POST /admin/backup` (Phase 5 scheduling).

## Risk Assessment
- **WAL torn copy** → mitigated by online-backup API + read-only open; do NOT `cp` the live DB.
- **Disk full mid-backup** → pre-flight check + always-run cleanup removes the partial dir (L50/L58).
- **Backup contains PII** → ACCEPTED here (security out of scope); flagged for the followups/security plan.
- **Wrong migration-head source** → verify the actual table name in `migrations.py` before relying on it.

## Red-Team Hardening (must-fix, 2026-06-24)
- **H1 — backup is a GATE, not a dump.** The manifest must be validated against the **LIVE source**, not computed only from the snapshot (else a snapshot that silently lost un-checkpointed rows records its own wrong count and "passes"). Steps: (1) `PRAGMA wal_checkpoint(TRUNCATE)` + `integrity_check` on the **live** source; (2) read live per-table row counts + content checksums; (3) `src.backup(dst)`; (4) read the snapshot's counts/checksums; (5) **assert delta == 0** or FAIL the backup. Manifest stores both `source_*` and `snapshot_*`.
- **H5 — content checksums, not just row counts.** Per table store `hash(group_concat(pk || '|' || <mutable cols> ORDER BY pk))` (Python-side). Row-count + file-sha pass even when values are silently corrupted (e.g. 500 phones NULLed).
- **Record `image_digest`** (`docker inspect crm --format '{{.Image}}'`) in the manifest — the drill must restore against the same image (else new migrations give false PASS).
- **H7 — per-DB success flags.** If `cache.db` fails but `crm.db` succeeded, keep `crm.db` + mark `manifest.partial=true`; don't discard the good DB in rotation.
- **Defender/dllhost lock (Windows):** write the backup dest to a **Docker named volume** (lives in the WSL2 VM), not a host bind under `app_data/` — host `.db` files get locked mid-write by Defender's `dllhost` (this project's recurring DuckDB issue; SQLite analog).
- **Disk safety:** 2× source-size headroom pre-flight; rotation runs BEFORE writing the new snapshot; keep backups off the shared `app_data/data_lake` tree (filling it breaks Dagster + Metabase).
- **Reconcile existing backups:** disable the `crm_data` copy leg in `scripts/backup/backup.sh` (line ~152 loop) and `backup.ps1` (Step 3) — they raw-copy WAL (unsafe) and create a confusing 2nd/3rd format. Declare this tool authoritative.
- **Silent-failure alerting:** emit a Lark alert (reuse `orchestration/notifications/lark_client.py` pattern) on backup failure; a silently-stopped backup = the zombie-run lesson repeating.
- **Dagster-trigger reality (corrected):** this runs via `docker exec crm …`; `data_platform` has NO docker socket. Keep the logic callable, but document that scheduling needs a CRM HTTP admin endpoint, a socket, or host cron — not a trivial Dagster op.

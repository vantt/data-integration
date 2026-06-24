# CRM DR Pilot — Lessons Learned (feeds warehouse DR plan)

Pilot: `plans/260624-2010-crm-backup-checkpoint-restore-verify` (Phases 1-3 done + verified).

## What worked
- **Backup-as-a-gate** (compare snapshot to the LIVE source, fail on delta≠0) is the
  single most important design choice — it turns "a file exists" into "a provably
  complete backup". Without it (manifest computed only from the snapshot) a silently
  truncated backup passes. (Red-team H1.)
- **SQLite online-backup API** (`Connection.backup()`) gives a consistent hot snapshot
  with zero app downtime — verified against a live 7572-party DB.
- **Restore-verify drill = the deliverable.** Booting a fresh, isolated app from the
  backup + asserting integrity (vs manifest) and function (serves real data), plus a
  **prod-untouched fingerprint assertion**, is what actually proves recoverability.
- **Negative tests are mandatory** — row-drop / value-mutation / table-truncate /
  file-truncate all correctly FAILed the drill, proving the checks aren't vacuous.

## Surprises / gotchas (Windows + Docker)
- Compose **prefixes volume names** (`data-integration_crm_backups`) — a bare
  `docker run -v crm_backups` silently creates an empty new volume. Resolve the real name.
- **CRLF entrypoint** breaks Linux `exec` (shebang `#!/bin/sh\r`) → mount an LF-normalized
  copy + invoke via `/bin/sh`.
- **cp1252 console** can't print box-drawing/emoji → force `sys.stdout.reconfigure(utf-8)`.
- **MSYS path mangling** (`/data` → `C:/Program Files/Git/data`) — run the drill via host
  Python (subprocess→docker direct), or `MSYS_NO_PATHCONV=1` for git-bash docker calls.
- **Baked entrypoint** — the `CRM_VERIFY_MODE` gate isn't in the running image until rebuild;
  mount it for the drill.
- At restore time, **sha256(file) is the dominant integrity check** (any byte change is
  caught). Content-checksums earn their keep at BACKUP time (source vs snapshot are
  different files).

## Deferred (carry into warehouse plan or a CRM follow-up)
Cross-version `--forward-migrate` drill · named-volume (vs host-bind) for drill `/data` ·
image-digest assert · FK-check in gate A · offsite automation · backup-age alerting · scheduling.

## Mapping to the WAREHOUSE (key differences)
- **Source of truth = the raw Parquet lake** (append-only; holds 2021-2025 Sapo history —
  `project_sapo_history_log_truncation`), `dagster_home` state, seeds. **Regenerable:**
  `sapo_warehouse.duckdb`, serving `olap.duckdb`, standalone export, all marts (dbt rebuilds them).
- **DuckDB has no SQLite-style online backup.** Don't try to byte-snapshot a live DuckDB.
  Instead: back up the **raw parquet + dagster_home + seeds**; "restore" = restore those →
  `dbt run` + serving build → **verify the rebuilt marts** (row counts / KPI invariants),
  NOT byte-identical files. This sidesteps DuckDB consistency entirely.
- **Reuse:** manifest+checksum gate (on parquet), isolated restore env, integrity +
  functional (a serving query / KPI invariant) checks, prod-untouched assertion, negative tests.
- **Existing assets:** `scripts/backup/backup.sh` (already backs up data_lake/dagster_home),
  `orchestration/ops/system_backup.py`; coordinate with C1 backup-security in `260624-1958-pipeline-hardening-followups`.

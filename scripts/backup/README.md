# Backup & Restore

Production runs on Linux with Docker. Three mechanisms back it up; none of them stops the data
pipeline. The PowerShell scripts at the end are the older Windows (Docker Desktop) variant and
are not used in production.

## What gets backed up in production

| Data | Path | How | When |
|------|------|-----|------|
| Data lake: raw (source of truth), `sapo_warehouse.duckdb` and `serving/` ("accelerator": used only if they open, dbt rebuilds them) | `app_data/data_lake/` except `monitoring/` | `backup.sh` (hot copy) | Nightly ~01:04 |
| Ingestion health history (`ingestion_health.db`, SQLite) | named volume `monitoring_db` | `backup.sh` → `sqlite_snapshot.py` (SQLite backup API) | Nightly |
| Dagster schedule/sensor state and cursors (`schedules/schedules.db`) + `dagster.yaml` | named volume `dagster_home` | `backup.sh` → `sqlite_snapshot.py` | Nightly |
| Warehouse tables that cannot be rebuilt from raw (`main.monitor_taxonomy_parity_log`) | inside `sapo_warehouse.duckdb` | `backup.sh` → `duckdb_snapshot.py` (parquet) | Nightly |
| Input files | `app_data/input_source/` | `backup.sh` | Nightly |
| Config files | `docker-compose.yml`, `Dockerfile.dataplatform`, `Dockerfile.metabase` (never `.env*`: a found secret file is removed and the run is marked `partial`) | `backup.sh` | Nightly |
| Metabase content as JSON (collections, cards, dashboards, users, groups, permissions, subscriptions) | `metabase_export/` inside each nightly backup | `metabase_export.py`, step of `backup.sh` | Nightly |
| Metabase H2 database (full restore point) + JSON export with the counts at copy time | `app_data/metabase_data/metabase.db.mv.db` | `metabase_cold_backup.sh` (cold copy, Metabase stopped ~20 s) | Nightly 00:30 + before deploys that write to Metabase |
| CRM SQLite | `app_data/crm_data/` | `crm/ops/backup_crm.py` (consistent snapshot) | `crm_backup_schedule`, 02:00 |

Not backed up: Dagster run history and event log (`dagster_home/history/`, purged daily) and
`dagster_home/storage/` (IO manager output, compute logs; regenerated), Caddy TLS certs
(`caddy_data` volume, regenerated), source code (git). All copies are on the same disk as the
data; the off-machine copy and the full data scope are described in
[docs/operations/backup-and-recovery.md](../../docs/operations/backup-and-recovery.md).

## backup.sh (nightly, inside data_platform)

Dagster job `maintain_backup_platform_job` (`orchestration/ops/system_backup.py`, op holding
`duckdb_lock`) runs `backup.sh` inside the `data_platform` container. It writes
`app_data/backups/<YYYYmmdd-HHMMSS>/` (container path `/app/var/backups`), keeps the newest
`BACKUP_KEEP_COUNT` (default 7) and writes `backup-<timestamp>.log` next to them.

Layout of one backup:

| Path | Content |
|---|---|
| `app_data/data_lake/` | hot copy of the lake without `monitoring/` |
| `app_data/monitoring/ingestion_health.db` | SQLite backup API copy, `integrity_check` ok |
| `app_data/dagster_home/schedules/schedules.db`, `dagster.yaml` | SQLite backup API copy + config |
| `app_data/input_source/` | hot copy |
| `exports/warehouse/<schema>.<table>.parquet` | `BACKUP_EXPORT_TABLES` (default `main.monitor_taxonomy_parity_log`) |
| `config/`, `metabase_export/` | as above |
| `manifest.json` | every component: `role` (`source_of_truth`, `accelerator`, `copy`), `state` (`ok`, `skipped`, `error`), size; sha256 and row counts for the SQLite copies and parquet exports |

`app_data/backups/status/local.json` holds the result of the last run: `state` is `ok`,
`partial` (the data copy succeeded but a snapshot failed: the job stays green, `errors` says
which) or `failed`. It is written even when the script aborts.

Check a backup against its manifest (sha256 and row counts):

```bash
docker exec data_platform python3 /app/scripts/backup/backup_manifest.py verify /app/var/backups/<YYYYmmdd-HHMMSS>
```

The container does not mount `metabase_data`, so the script does not copy the Metabase H2 file.
Its Metabase step runs `metabase_export.py`, which reads the Metabase API at `METABASE_URL`
(`http://metabase:3000` on `caddy_net`) with `METABASE_API_KEY` from `.env.docker` and writes
JSON files plus `manifest.json` (counts, Metabase version). The key is never printed. An export
failure is logged as a warning and does not fail the backup.

Run by hand inside the container:

```bash
docker exec data_platform bash /app/scripts/backup/backup.sh
docker exec data_platform python3 /app/scripts/backup/metabase_export.py /tmp/mb-export   # export only
```

## Metabase

`metabase_cold_backup.sh` runs on the host: it stops the `metabase` container, copies
`metabase.db.mv.db` to `app_data/backups/metabase/metabase-<nightly|pre-deploy>-<timestamp>.mv.db`,
starts Metabase and waits for `/api/health`. Once healthy it exports the content through the API
into `<copy>.export/` (its `manifest.json` holds the counts at copy time; only `METABASE_API_KEY`
is read from `.env.docker`, never printed; a failed export is a warning). It keeps 7 copies per
kind (`METABASE_COLD_KEEP`), logs to `app_data/backups/metabase/cold-backup.log` and writes
`app_data/backups/status/metabase_cold.json`. Exit code 0 only when the copy is complete and
Metabase is healthy again. Copies of the earlier kind `weekly` are left until removed by hand.

```bash
scripts/backup/metabase_cold_backup.sh pre-deploy   # before a deploy that writes to Metabase
```

The nightly run is a systemd user timer (00:30). The units are generated from the templates in
`systemd/*.in` (no hard-coded checkout path) by `install-units.sh`:

```bash
scripts/backup/install-units.sh                     # render into ~/.config/systemd/user, reload, enable every timer
scripts/backup/install-units.sh --no-enable         # render + reload only
scripts/backup/install-units.sh --unit-dir /tmp/u   # render only (review), nothing installed
systemctl --user list-timers metabase-cold-backup.timer
```

Run it from the checkout the units should use (or pass `--project-root`). Lingering must be on
for the user (`loginctl show-user "$USER" -p Linger` shows `Linger=yes`), otherwise the timer
only runs while someone is logged in; the script warns when it is off. To change the time, edit
`OnCalendar` in `systemd/metabase-cold-backup.timer.in` and run `install-units.sh` again.

Restore steps: `docs/operations/deployment.md`, section "Metabase: backup and restore".

## Legacy: Windows (Docker Desktop) scripts

`backup.ps1`, `restore.ps1` and `setup-task-scheduler.ps1` were written for the earlier Windows
deployment. They stop all containers, mirror the whole `app_data/` (Metabase included) with
`robocopy`, and start the containers again. They are kept for that setup only.

```powershell
.\backup.ps1 [-BackupRoot "E:\backups"] [-KeepCount 14] [-SkipRestart]
.\setup-task-scheduler.ps1 [-Time "03:00"] [-Unregister]      # daily scheduled task, as Administrator
.\restore.ps1 -BackupDir "<backup dir>" [-DryRun] [-Force]
```

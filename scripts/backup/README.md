# Backup & Restore

Production runs on Linux with Docker. Three mechanisms back it up; none of them stops the data
pipeline. The PowerShell scripts at the end are the older Windows (Docker Desktop) variant and
are not used in production.

## What gets backed up in production

| Data | Path | How | When |
|------|------|-----|------|
| Data lake (DuckDB + Parquet) | `app_data/data_lake/` | `backup.sh` (hot copy) | Nightly ~01:04 |
| Dagster state (without run history) | `app_data/dagster_home/` | `backup.sh` | Nightly |
| Input files | `app_data/input_source/` | `backup.sh` | Nightly |
| Config files | `docker-compose.yml`, `Dockerfile.dataplatform`, `Dockerfile.metabase` (`.env.docker` is not mounted in the container, so it is **not** copied) | `backup.sh` | Nightly |
| Metabase content as JSON (collections, cards, dashboards, users, groups, permissions, subscriptions) | `metabase_export/` inside each nightly backup | `metabase_export.py`, step of `backup.sh` | Nightly |
| Metabase H2 database (full restore point) | `app_data/metabase_data/metabase.db.mv.db` | `metabase_cold_backup.sh` (cold copy, Metabase stopped 1-2 min) | Weekly Sunday 00:30 + before deploys that write to Metabase |
| CRM SQLite | `app_data/crm_data/` | `crm/ops/backup_crm.py` (consistent snapshot) | `crm_backup_schedule` |

Not backed up: Caddy TLS certs (`caddy_data` volume, regenerated), source code (git), Dagster
run history (pruned on purpose). All copies are on the same disk as the data; there is no
off-machine copy yet.

## backup.sh (nightly, inside data_platform)

Dagster job `maintain_backup_platform_job` (`orchestration/ops/system_backup.py`) runs
`backup.sh` inside the `data_platform` container. It copies the directories above from
`/app/var/` into `app_data/backups/<YYYYmmdd-HHMMSS>/` (container path `/app/var/backups`),
keeps the newest `BACKUP_KEEP_COUNT` (default 7) and writes `backup-<timestamp>.log` next to them.

The container does not mount `metabase_data`, so the script does not copy the Metabase H2 file.
Its step 2b runs `metabase_export.py`, which reads the Metabase API at `METABASE_URL`
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
`metabase.db.mv.db` to `app_data/backups/metabase/metabase-<weekly|pre-deploy>-<timestamp>.mv.db`,
starts Metabase and waits for `/api/health`. It keeps 7 copies per kind (`METABASE_COLD_KEEP`)
and logs to `app_data/backups/metabase/cold-backup.log`. Exit code 0 only when the copy is
complete and Metabase is healthy again.

```bash
scripts/backup/metabase_cold_backup.sh pre-deploy   # before a deploy that writes to Metabase
```

The weekly run is a systemd user timer (files in `systemd/`). Install or update it:

```bash
mkdir -p ~/.config/systemd/user
cp scripts/backup/systemd/metabase-cold-backup.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now metabase-cold-backup.timer
systemctl --user list-timers metabase-cold-backup.timer   # next run
```

Lingering must be on for user `vantt` (`loginctl show-user vantt -p Linger` shows
`Linger=yes`), otherwise the timer only runs while someone is logged in. To change the time, edit
`OnCalendar` in the timer file and repeat the install steps.

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

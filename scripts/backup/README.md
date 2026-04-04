# Backup & Restore

Automated backup for the Data Integration Platform running on Docker Desktop (Windows).

## What gets backed up

| Data | Path | Size | Priority |
|------|------|------|----------|
| Data Lake (DuckDB + Parquet) | `app_data/data_lake/` | Large | **Critical** |
| Metabase (H2 DB — dashboards, questions) | `app_data/metabase_data/` | Small | **Critical** |
| Dagster (run history, schedules) | `app_data/dagster_home/` | Medium | Nice-to-have |
| Logs | `app_data/logs/` | Small | Low |
| Config files | `.env.docker`, `docker-compose.yml`, Dockerfiles | Tiny | **Critical** |

## How it works

1. `docker compose stop` — ensures data consistency (especially Metabase H2 DB)
2. `robocopy /MIR` — mirror `app_data/` to timestamped backup folder
3. `docker compose start` — bring services back up
4. Rotate old backups (default: keep 7)

**Downtime**: ~1-5 minutes depending on data size.

## Quick start

```powershell
# Run backup manually
.\backup.ps1

# Custom backup location
.\backup.ps1 -BackupRoot "E:\backups"

# Keep 14 backups instead of 7
.\backup.ps1 -KeepCount 14

# Backup without restarting (maintenance window)
.\backup.ps1 -SkipRestart
```

## Automate with Task Scheduler

```powershell
# Run as Administrator — creates daily task at 2:00 AM
.\setup-task-scheduler.ps1

# Change schedule time
.\setup-task-scheduler.ps1 -Time "03:00"

# Remove scheduled task
.\setup-task-scheduler.ps1 -Unregister

# Verify
Get-ScheduledTask -TaskName "DataIntegration-Backup"

# Test run
Start-ScheduledTask -TaskName "DataIntegration-Backup"
```

## Restore

```powershell
# List available backups
Get-ChildItem "D:\_1.FWG_PARA\1.Projects\dev\dataware_house\backups" -Directory

# Dry run (preview what would happen)
.\restore.ps1 -BackupDir "D:\...\backups\20260404-020000" -DryRun

# Actual restore (will prompt for confirmation)
.\restore.ps1 -BackupDir "D:\...\backups\20260404-020000"
```

## Backup structure

```
backups/
├── 20260404-020000/
│   ├── app_data/
│   │   ├── data_lake/      # DuckDB + parquet files
│   │   ├── metabase_data/  # H2 database
│   │   ├── dagster_home/   # Run history
│   │   └── logs/
│   └── config/
│       ├── .env.docker
│       ├── docker-compose.yml
│       ├── Dockerfile.dataplatform
│       └── Dockerfile.metabase
├── 20260403-020000/
├── backup-20260404-020000.log
└── backup-20260403-020000.log
```

## Defaults

| Setting | Default | Override |
|---------|---------|---------|
| Project root | `D:\_1.FWG_PARA\...\data-integration2` | `-ProjectRoot` |
| Backup root | `D:\_1.FWG_PARA\...\backups` | `-BackupRoot` |
| Keep count | 7 | `-KeepCount` |
| Schedule time | 02:00 | `-Time` (in setup script) |

## Notes

- **Caddy TLS certs** (`caddy_data` Docker volume) are NOT backed up — they auto-regenerate for local dev.
- **Metabase H2 consistency**: Containers are stopped before backup to avoid corrupt H2 files. If you need zero-downtime, consider migrating Metabase to PostgreSQL.
- **Source code** is NOT backed up here (use git for that).
- Logs are in `backups/backup-{timestamp}.log`.

# Configuration Guide

## Overview

Platform config uses a layered approach: sensible defaults in config files, credentials and environment-specific overrides in `.env` files.

## Config Layers (High → Low Precedence)

```
1. docker-compose environment:   ← container constants (tied to mounts/infra)
2. .env.docker  (via env_file:)  ← credentials + env-specific overrides
3. .env.local   (project root)   ← local dev overrides (loaded by config loader)
4. secrets.toml (ingestion/.dlt/) ← dlt credentials (alternative to env)
5. config.toml  (ingestion/.dlt/) ← dlt defaults (layout, format, selectors)
```

Higher layers override lower ones. In Docker, layer 1+2 are primary. For local dev without Docker, layer 3 is used.

## File Locations

| File | Location | Committed? | Purpose |
|------|----------|-----------|---------|
| `.env.example` | project root | Yes | Template — copy to `.env.docker` or `.env.local` |
| `.env.docker` | project root | No (gitignored) | Docker runtime config |
| `.env.local` | project root | No (gitignored) | Local dev config |
| `config.toml` | `ingestion/.dlt/` | Yes | dlt defaults (rarely change) |
| `secrets.toml` | `ingestion/.dlt/` | No (gitignored) | dlt credentials (alternative to env vars) |
| `dagster.yaml` | `app_data/dagster_home/` | Yes (mounted) | Dagster instance config (concurrency, retention) |
| `dbt_project.yml` | `transformation/` | Yes | dbt project structure, seeds, materialization |
| `profiles.yml` | `transformation/` | Yes | dbt DuckDB connection, reads `DBT_*` env vars |
| `ingestion_sla.yaml` | `orchestration/config/` | Yes | Asset freshness SLA definitions |

## .env.example Conventions

```bash
# Uncommented  = must be set by operator (credentials, env-specific paths)
SOURCES__SAPO__USERNAME="your_username_here"

# Commented    = has default elsewhere, shown for discoverability
# DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT=parquet
```

Organized by sections: `[SHARED]`, `[DATA PLATFORM — *]`, `[METABASE]`, `[RILL]`.

## What Lives Where

### config.toml owns (defaults, rarely change):
- `destination.filesystem.loader_file_format` (parquet)
- `destination.filesystem.layout` (partition template)
- `destination.filesystem.extra_placeholders`
- `sources.sapo.request_delay`, `headless`, `login_selectors`
- `sources.spreadsheet_url.*` (Google Sheets URLs)
- `sources.shopee.input_dir`, `file_pattern`
- `sources.misa_amis.input_dir`, `file_pattern`

### .env owns (credentials + environment-specific):
- `SOURCES__SAPO__USERNAME`, `PASSWORD` (credentials)
- `DESTINATION__FILESYSTEM__BUCKET_URL` (path differs per environment)
- `DBT_EXPORT_PATH`, `DBT_DATA_LAKE_PATH` (paths)
- `WORKER_URL` (webhook endpoint)
- `METABASE_API_KEY`, `LARK_ALERT_*` (credentials)
- `BACKUP_KEEP_COUNT` (operator preference)

### docker-compose environment: owns (container constants tied to mounts/infra):
- `BACKUP_ROOT=/app/backups` — tied to volume mount, cannot change independently
- `DLT_TELEMETRY_DISABLED=true`
- `DBT_SEND_ANONYMOUS_USAGE_STATS=false`

### Dockerfile ENV owns (build-time, immutable):
- `DAGSTER_HOME=/app/.dagster_home`
- `PYTHONPATH=/app`
- `DBT_PROJECT_DIR=/app/transformation`
- `DBT_PROFILES_DIR=/app/transformation`

## Path Consistency

Config files are mounted into Docker at the **same relative path** as on the host — both use project root. This ensures scripts work identically in both environments:

| Environment | Project root | Example config path |
|-------------|-------------|-------------------|
| Host (Windows) | `D:\Vantt\app\data-integration` | `$ProjectRoot/.env.docker` |
| Docker (Linux) | `/app` | `/app/.env.docker` |

Volume mounts in docker-compose.yml:
```yaml
- ./.env.docker:/app/.env.docker:ro
- ./docker-compose.yml:/app/docker-compose.yml:ro
```

`backup.sh` (Docker) and `backup.ps1` (Windows) both use `${PROJECT_ROOT}/${filename}` — same logic, no special-casing.

## Tool-Specific Configs

### dlt (ingestion)
- `config.toml` — committed defaults (layout, format, source settings)
- `secrets.toml` — gitignored credentials (alternative to env vars)
- dlt resolves `.dlt/` relative to CWD — assets must `os.chdir(DLT_DIR)` before pipeline

### dbt (transformation)
- `dbt_project.yml` — model structure, seeds, materialization
- `profiles.yml` — DuckDB connection, reads `{{ env_var('DBT_DATA_LAKE_PATH') }}`

### Dagster (orchestration)
- `dagster.yaml` — concurrency limits (`dbt_rw: 1`), retention, telemetry
- `ingestion_sla.yaml` — per-asset freshness SLAs

## Config Loading Flow

### Docker (production)
```
docker-compose up
  → env_file: .env.docker → os.environ (all vars available)
  → environment: → container constants override (BACKUP_ROOT, telemetry)
  → Dagster starts, imports definitions.py
    → load_dlt_configuration() verifies credentials present
    → dlt reads config.toml natively (via os.chdir)
    → dbt reads profiles.yml with {{ env_var() }}
```

### Local dev (without Docker)
```
Copy .env.example → .env.local, fill in credentials (adjust paths to Windows)
  → Run Dagster or script
    → load_dlt_configuration() parses .env.local → os.environ
    → load_dlt_configuration() parses secrets.toml → os.environ (lower precedence)
    → Same dlt/dbt resolution as Docker
```

## Adding New Config Variables

1. Decide owner: is it a default (config.toml) or environment-specific (.env)?
2. If tied to a Docker volume mount → put in docker-compose `environment:` with comment
3. Add to `.env.example` — uncommented if required, commented if has default
4. Place in the correct section of `.env.example`
5. If consumed by dbt: use `{{ env_var('VAR_NAME') }}` in profiles.yml
6. If consumed by Python: use `os.environ.get('VAR_NAME', 'default')`

## Backup

Config files (`.env.docker`, `docker-compose.yml`, Dockerfiles) are mounted read-only at `/app/` inside Docker and backed up daily by `platform_backup_job` to `$BACKUP_ROOT/{timestamp}/config/`.

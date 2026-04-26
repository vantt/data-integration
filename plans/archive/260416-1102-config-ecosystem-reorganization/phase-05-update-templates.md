# Phase 5: Update .env.example + Docs

## Context
- [.env.example](../../.env.example) — current 85-line monolithic template
- [phase-04](phase-04-clean-compose-env.md) — prerequisite
- [plan.md](plan.md)

## Overview
- **Priority**: P2
- **Status**: Pending
- **Effort**: 20m
- **Blocked by**: Phase 4

## Problem
`.env.example` still reflects the old monolithic structure. After Phases 1-4, the config ecosystem has changed. Template must match reality.

## Architecture

### New Template Files
Replace single `.env.example` with 3 templates mirroring the new structure:

```
.env.example                      # DELETE (replaced by per-service templates)
.env.shared.docker.example        # TZ only
.env.data-platform.docker.example # data_platform vars
.env.metabase.docker.example      # metabase vars
```

### "Documented Defaults" Pattern

Each template uses this convention:
```env
# --- Section Name ---
# Description of what these vars control

# Required — no default, must be set:
SOURCES__SAPO__USERNAME="your_username_here"

# Optional — has default in config.toml (shown for reference):
# DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT=parquet
# DESTINATION__FILESYSTEM__LAYOUT={table_name}/ingest_method=...
```

- **Uncommented** = must be set by operator (credentials, env-specific paths)
- **Commented with value** = has default elsewhere (config.toml or Dockerfile), shown for discoverability. Uncomment to override.

### .env.data-platform.docker.example Content

```env
# ==========================================
# DATA PLATFORM CONFIG — data_platform service
# ==========================================
# Copy to .env.data-platform.docker and fill in credentials.
# Vars with defaults in config.toml are commented out — uncomment to override.

# --- Sapo API Credentials ---
SOURCES__SAPO__DOMAIN=fwg.mysapogo.com
SOURCES__SAPO__USERNAME="your_username_here"
SOURCES__SAPO__PASSWORD="your_password_here"
SOURCES__SAPO__HEADLESS=true

# --- Destination ---
DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/data_lake
# Default in config.toml — uncomment to override:
# DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT=parquet
# DESTINATION__FILESYSTEM__LAYOUT={table_name}/ingest_method={ingest_method}/year={year}/month={month}/{file_id}.{ext}
# DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS={"ingest_method": "text", "year": "text", "month": "text"}

# --- Orchestration ---
DAGSTER_PORT=3001
DBT_EXPORT_PATH=/app/data_lake/export/marts
DBT_DATA_LAKE_PATH=/app/data_lake

# --- Webhook Consumer ---
WORKER_URL=http://localhost:8787
POLL_LIMIT=100
SLEEP_INTERVAL=5
MIN_SLEEP_INTERVAL=10
MAX_SLEEP_INTERVAL=60

# --- Alerting ---
LARK_ALERT_WEBHOOK="your_webhook_url"
LARK_ALERT_SECRET="your_secret"

# --- Metabase Provisioning (scripts only) ---
METABASE_URL=http://metabase:3000/
METABASE_API_KEY="mb_your_api_key_here"
METABASE_DB_NAME=Sapo

# --- Backup ---
BACKUP_ROOT=/app/backups
BACKUP_KEEP_COUNT=7

# --- Sheets Sensor (optional — defaults read from config.toml) ---
# SHEETS_SENSOR_TARGETS_URL=https://docs.google.com/.../export?format=csv
# SHEETS_SENSOR_MARKETING_URL=https://docs.google.com/.../export?format=csv

# --- Timeouts (optional — have code defaults) ---
# SERVING_TIMEOUT_SEC=1800
# RILL_PUBLISH_TIMEOUT_SEC=900
# INGESTION_HEALTH_DB=/app/data_lake/ingestion_health.duckdb
```

### Docs Updates

Files referencing old config structure:
- `.skills/data-pipeline/SKILL.md` line 163 — references `load_dlt_configuration()`
- `.skills/data-pipeline/lessons-learned.md` L10 — references the loader
- `.skills/data-pipeline/troubleshooting.md` — references the loader
- `.skills/data-pipeline/templates/dagster-asset-template.py` — uses old function
- `orchestration/docs/RESOURCES.md` line 60 — references the loader
- `docs/dlt-ingestion-skill-design.md` — references the loader

## Related Code Files
- **Create**: `.env.shared.docker.example`, `.env.data-platform.docker.example`, `.env.metabase.docker.example`
- **Delete**: `.env.example` (replaced by per-service templates)
- **Modify**: `.gitignore` — ensure new patterns covered
- **Modify**: `.skills/data-pipeline/SKILL.md`, `lessons-learned.md`, `troubleshooting.md`, `dagster-patterns.md`
- **Modify**: `orchestration/docs/RESOURCES.md`
- **Modify**: `docs/dlt-ingestion-skill-design.md`

## Implementation Steps

1. Create `.env.shared.docker.example`:
   ```env
   # Shared across all services
   TZ=Asia/Ho_Chi_Minh
   ```
2. Create `.env.data-platform.docker.example` (content above)
3. Create `.env.metabase.docker.example`:
   ```env
   # METABASE CONFIG — metabase service
   MB_DB_TYPE=h2
   MB_DB_FILE=/home/metabase/data/metabase.db
   # Uncomment for Postgres:
   # MB_DB_DBNAME=metabase
   # MB_DB_PORT=5432
   # MB_DB_USER=metabase
   # MB_DB_PASS=metabase
   # MB_DB_HOST=metabase_db
   ```
4. Delete `.env.example`
5. Update all doc files referencing `load_dlt_configuration` → `verify_dlt_config`
6. Update RESOURCES.md config section to describe new 3-layer model
7. Verify `.gitignore` has `.env.*.docker` pattern (added in Phase 1)

## Todo
- [ ] Create .env.shared.docker.example
- [ ] Create .env.data-platform.docker.example
- [ ] Create .env.metabase.docker.example
- [ ] Delete .env.example
- [ ] Update .skills/data-pipeline/SKILL.md
- [ ] Update .skills/data-pipeline/lessons-learned.md
- [ ] Update .skills/data-pipeline/troubleshooting.md
- [ ] Update .skills/data-pipeline/dagster-patterns.md
- [ ] Update orchestration/docs/RESOURCES.md
- [ ] Update docs/dlt-ingestion-skill-design.md

## Success Criteria
- `ls .env.*.example` returns 3 files
- `.env.example` no longer exists
- `grep -r "load_dlt_configuration" .skills/ docs/ orchestration/docs/` returns 0 matches
- New operator can set up project by copying 3 .example files and filling in credentials

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed a doc reference | Medium | Low | Grep sweep in Phase 6 validation catches stragglers |
| Operator confusion (3 files vs 1) | Low | Low | Header comments in each file explain the setup clearly |

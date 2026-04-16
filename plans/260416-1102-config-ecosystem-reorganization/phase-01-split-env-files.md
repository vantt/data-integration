# Phase 1: Split .env.docker into Per-Service Files

## Context
- [docker-compose.yml](../../docker-compose.yml) — service definitions
- [.env.example](../../.env.example) — current template
- [plan.md](plan.md)

## Overview
- **Priority**: P1 — foundation for all subsequent phases
- **Status**: Pending
- **Effort**: 45m

## Problem
Single `.env.docker` shared by ALL services via `env_file:`. Metabase receives Sapo passwords, DAGSTER_PORT, BACKUP_ROOT — vars it never reads. Violates least-privilege.

## Architecture

### New File Structure
```
.env.data-platform.docker    # data_platform service only
.env.metabase.docker          # metabase service only
.env.shared.docker            # shared vars (TZ only today)
```

### Variable Ownership Map

**.env.shared.docker** (injected into both services):
```env
TZ=Asia/Ho_Chi_Minh
```

**.env.data-platform.docker** (data_platform only):
```env
# --- Sapo API Credentials ---
SOURCES__SAPO__DOMAIN=fwg.mysapogo.com
SOURCES__SAPO__USERNAME=...
SOURCES__SAPO__PASSWORD=...
SOURCES__SAPO__HEADLESS=true

# --- Destination (only bucket_url — rest lives in config.toml) ---
DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/data_lake

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
LARK_ALERT_WEBHOOK=...
LARK_ALERT_SECRET=...

# --- Metabase Provisioning (scripts only) ---
METABASE_URL=http://metabase:3000/
METABASE_API_KEY=...
METABASE_DB_NAME=Sapo
```

**.env.metabase.docker** (metabase only):
```env
MB_DB_TYPE=h2
MB_DB_FILE=/home/metabase/data/metabase.db
```

### docker-compose.yml Changes
```yaml
services:
  data_platform:
    env_file:
      - .env.shared.docker
      - .env.data-platform.docker
    # ... rest unchanged

  metabase:
    env_file:
      - .env.shared.docker
      - .env.metabase.docker
    # ... rest unchanged
```

## Related Code Files
- **Modify**: `docker-compose.yml` (env_file arrays)
- **Create**: `.env.shared.docker`, `.env.data-platform.docker`, `.env.metabase.docker`
- **Delete**: `.env.docker` (after migration validated)
- **Modify**: `.gitignore` (add new env file patterns)
- **Modify**: `scripts/backup/backup.sh` line 94 — references `.env.docker`
- **Modify**: `scripts/backup/backup.ps1` line 106 — references `.env.docker`
- **Modify**: `scripts/secure_deploy.ps1` line 8 — references `.env.docker`

## Implementation Steps

1. Create `.env.shared.docker` with `TZ=Asia/Ho_Chi_Minh`
2. Create `.env.data-platform.docker` — move data_platform vars from current `.env.docker`
3. Create `.env.metabase.docker` — move metabase-only vars (MB_DB_TYPE, MB_DB_FILE)
4. Update `docker-compose.yml`:
   - `data_platform.env_file` → list of `.env.shared.docker` + `.env.data-platform.docker`
   - `metabase.env_file` → list of `.env.shared.docker` + `.env.metabase.docker`
   - Remove bind-mount of `.env.docker` (line 34): `- ./.env.docker:/app/.env.docker:ro`
5. Update `.gitignore`: add `.env.*.docker` pattern, keep `.env.docker` entry for safety
6. Update backup scripts to copy new env files instead of `.env.docker`
7. Keep old `.env.docker` as `.env.docker.bak` until Phase 6 validates

## Todo
- [ ] Create .env.shared.docker
- [ ] Create .env.data-platform.docker
- [ ] Create .env.metabase.docker
- [ ] Update docker-compose.yml env_file references
- [ ] Remove .env.docker bind-mount from volumes
- [ ] Update .gitignore
- [ ] Update backup.sh to reference new files
- [ ] Update backup.ps1 to reference new files
- [ ] Update secure_deploy.ps1 to reference new files

## Success Criteria
- `docker compose config` shows each service receives only its own vars
- Metabase container env does NOT contain SOURCES__SAPO__* or BACKUP_*
- data_platform container env does NOT contain MB_DB_*

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Forgot a var in wrong file | Medium | Low | `docker compose exec data_platform env \| sort` to verify |
| Backup scripts break | Low | Medium | Update in same phase; test backup manually |
| .env.docker mount used by app code | Low | High | Grep confirmed only backup.sh reads it; mount is ro convenience |

## Security
- New files remain gitignored — no secrets leak
- Service isolation = least-privilege improvement

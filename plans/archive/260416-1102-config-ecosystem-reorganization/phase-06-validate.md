# Phase 6: Validate & Smoke Test

## Context
- All prior phases completed
- [plan.md](plan.md)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Effort**: 30m
- **Blocked by**: Phase 5

## Purpose
Verify the entire config reorganization works end-to-end before deploying. This phase is read-only validation — no code changes.

## Validation Checklist

### 1. Static Checks (no Docker needed)

```bash
# No duplication — DESTINATION layout/format only in config.toml
grep -r "DESTINATION__FILESYSTEM__LAYOUT" --include="*.docker" .
# Expected: 0 matches

# No old loader references in orchestration code
grep -r "load_dlt_configuration" orchestration/
# Expected: 0 matches

# No old .env.docker references in docker-compose
grep "\.env\.docker" docker-compose.yml
# Expected: 0 matches (replaced with per-service files)

# utils.py is small
wc -l orchestration/assets/utils.py
# Expected: <30 lines

# All 3 example files exist
ls .env.*.docker.example
# Expected: shared, data-platform, metabase

# Old .env.example is gone
test -f .env.example && echo "FAIL: .env.example still exists" || echo "OK"

# gitignore covers new files
grep "env.*docker" .gitignore
# Expected: pattern matching .env.*.docker
```

### 2. Docker Compose Config Validation

```bash
# Syntax check — catches YAML errors
docker compose config --quiet

# Verify service isolation
docker compose config | grep -A 50 "data_platform:" | grep "env_file" -A 5
# Expected: .env.shared.docker + .env.data-platform.docker

docker compose config | grep -A 30 "metabase:" | grep "env_file" -A 5
# Expected: .env.shared.docker + .env.metabase.docker

# Verify environment block is minimal
docker compose config | grep -A 10 "environment:" 
# data_platform: only DLT_TELEMETRY_DISABLED + DBT_SEND_ANONYMOUS_USAGE_STATS
```

### 3. Container Smoke Test

```bash
# Rebuild and start
docker compose up -d --build --force-recreate

# Verify data_platform has correct vars
docker exec data_platform env | sort | grep -E "^(SOURCES__|DESTINATION__|DAGSTER_|DBT_|BACKUP_|TZ=)"
# Expected: all data_platform vars present

# Verify data_platform does NOT have metabase vars
docker exec data_platform env | grep "^MB_"
# Expected: 0 matches

# Verify metabase has correct vars
docker exec metabase env | sort | grep -E "^(MB_|TZ=)"
# Expected: MB_DB_TYPE, MB_DB_FILE, TZ

# Verify metabase does NOT have data_platform vars
docker exec metabase env | grep -E "^(SOURCES__|BACKUP_|DAGSTER_)"
# Expected: 0 matches

# Verify dlt config resolution
docker exec data_platform python -c "
import os, tomllib
os.chdir('/app/ingestion')
with open('.dlt/config.toml', 'rb') as f:
    cfg = tomllib.load(f)
fmt = cfg['destination']['filesystem']['loader_file_format']
assert fmt == 'parquet', f'Expected parquet, got {fmt}'
print('OK: config.toml resolution works')
"
```

### 4. Pipeline Smoke Test

```bash
# Trigger a quick Dagster job to verify config loads
# Use the Dagster UI or:
docker exec data_platform dagster job execute -f orchestration/definitions.py -j sheets_sync_job --run-id smoke-test-config
# Watch logs for:
# - "[Config] Verified: Sapo credentials present in environment."
# - No "MISSING" warnings
# - dlt picks up layout/format from config.toml
```

### 5. Backup Script Test

```bash
# Verify backup script references updated files
docker exec data_platform cat /app/scripts/backup/backup.sh | grep "env"
# Expected: references .env.shared.docker, .env.data-platform.docker, .env.metabase.docker
```

## Todo
- [ ] Run static checks (grep, wc, ls)
- [ ] Run docker compose config validation
- [ ] Rebuild containers and verify env isolation
- [ ] Verify dlt config.toml resolution inside container
- [ ] Run one pipeline job as smoke test
- [ ] Verify backup script references
- [ ] Delete .env.docker.bak (kept from Phase 1)

## Success Criteria
- All static checks pass (0 unexpected matches)
- docker compose config parses without errors
- data_platform container: has all its vars, none of metabase's
- metabase container: has all its vars, none of data_platform's
- At least one pipeline job completes successfully
- Backup script runs without file-not-found errors

## Rollback Procedure
If validation fails:
1. `git checkout -- docker-compose.yml orchestration/ .gitignore`
2. Restore `.env.docker` from `.env.docker.bak`
3. `docker compose up -d --force-recreate`
4. System returns to pre-change state in <2 minutes

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pipeline fails due to missing var | Low | High | Env dump check (step 3) catches before pipeline test |
| Metabase fails to start | Low | Medium | MB_DB_TYPE + MB_DB_FILE are simple; docker logs reveal instantly |
| dlt config.toml not found | Very Low | High | os.chdir(DLT_DIR) unchanged; Python snippet validates |

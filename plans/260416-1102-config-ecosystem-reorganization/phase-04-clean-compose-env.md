# Phase 4: Clean docker-compose environment Block

## Context
- [docker-compose.yml](../../docker-compose.yml) — lines 17-21 (data_platform environment)
- [Dockerfile.dataplatform](../../Dockerfile.dataplatform) — lines 36-39 (build-time ENV)
- [phase-03](phase-03-kill-config-loader.md) — prerequisite
- [plan.md](plan.md)

## Overview
- **Priority**: P2
- **Status**: Pending
- **Effort**: 20m
- **Blocked by**: Phase 3

## Problem
`docker-compose.yml` `environment:` block has 5 hardcoded vars that silently override `.env` files:
```yaml
environment:
  - DAGSTER_HOME=/app/.dagster_home       # also in Dockerfile ENV
  - DLT_TELEMETRY_DISABLED=true           # container-internal constant ✓
  - DBT_SEND_ANONYMOUS_USAGE_STATS=false  # container-internal constant ✓
  - BACKUP_ROOT=/app/backups              # overrides .env.docker silently!
  - BACKUP_KEEP_COUNT=7                   # overrides .env.docker silently!
```

Problems:
1. `DAGSTER_HOME` set in BOTH Dockerfile (line 36) AND docker-compose (line 17) — redundant
2. `BACKUP_ROOT=/app/backups` silently overrides any value in .env file — operator changes .env but container ignores it
3. `BACKUP_KEEP_COUNT=7` same silent override problem

## Design Rule
**docker-compose `environment:`** = ONLY container-internal constants that:
- Never need operator override, AND
- Are not already set in Dockerfile ENV, AND
- Are tooling flags (telemetry, analytics opt-outs)

## Architecture

### Target State

**data_platform `environment:`** — keep only telemetry flags:
```yaml
environment:
  - DLT_TELEMETRY_DISABLED=true
  - DBT_SEND_ANONYMOUS_USAGE_STATS=false
```

**Moved to `.env.data-platform.docker`** (operator-controllable):
```env
BACKUP_ROOT=/app/backups
BACKUP_KEEP_COUNT=7
```

**Removed (already in Dockerfile):**
- `DAGSTER_HOME=/app/.dagster_home` — Dockerfile line 36 sets this at build time

**rill `environment:`** — unchanged (already clean):
```yaml
environment:
  - RILL_EXPORT_ROOT=/app/data_lake/export/rill/current
  - TZ=Asia/Ho_Chi_Minh
```
Note: rill has no env_file (intentional — it needs almost nothing). `TZ` stays here since rill doesn't use `.env.shared.docker`.

### Data Flow
```
Dockerfile ENV           → DAGSTER_HOME (build-time, immutable)
.env.data-platform.docker → BACKUP_ROOT, BACKUP_KEEP_COUNT (operator-editable)
docker-compose environment → DLT_TELEMETRY_DISABLED, DBT_SEND_ANONYMOUS_USAGE_STATS (constants)
```

## Related Code Files
- **Modify**: `docker-compose.yml` — trim environment block, add rill env_file
- **Modify**: `.env.data-platform.docker` — add BACKUP_ROOT, BACKUP_KEEP_COUNT

## Implementation Steps

1. Move `BACKUP_ROOT=/app/backups` and `BACKUP_KEEP_COUNT=7` to `.env.data-platform.docker`
2. Remove `DAGSTER_HOME`, `BACKUP_ROOT`, `BACKUP_KEEP_COUNT` from docker-compose `environment:`
3. Keep `DLT_TELEMETRY_DISABLED=true` and `DBT_SEND_ANONYMOUS_USAGE_STATS=false`
4. Optionally add `.env.shared.docker` to rill's `env_file:` (for TZ) and remove `TZ` from rill `environment:` — but this is low-value; rill also passes env via `--env` flag in command. Skip unless we want consistency.

## Todo
- [ ] Move BACKUP_ROOT + BACKUP_KEEP_COUNT to .env.data-platform.docker
- [ ] Remove DAGSTER_HOME from docker-compose environment (Dockerfile handles it)
- [ ] Keep only telemetry flags in environment block
- [ ] Verify `docker compose config` shows correct precedence

## Success Criteria
- `docker compose config` data_platform.environment has exactly 2 entries (telemetry flags)
- BACKUP_ROOT value in running container matches .env.data-platform.docker (not hardcoded)
- DAGSTER_HOME still resolves (from Dockerfile ENV)

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DAGSTER_HOME missing if Dockerfile changes | Very Low | High | It's set at build time; docker build would fail visibly |
| Operator forgets BACKUP_ROOT in new env file | Low | Medium | Phase 5 .env.example documents it with default value |

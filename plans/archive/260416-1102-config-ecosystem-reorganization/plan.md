---
title: "Config Ecosystem Reorganization"
description: "Eliminate config duplication, isolate service env vars, kill custom loader"
status: done-pragmatic
priority: P2
effort: 3h (planned) / ~1.5h (actual)
branch: main
tags: [config, devops, cleanup]
created: 2026-04-16
completed: 2026-04-16
commit: d0a4da3
---

# Config Ecosystem Reorganization

## Goal
Reduce 5 overlapping config layers to 3 clean ones: `config.toml` (defaults) + `.env.*.docker` (credentials/overrides per service) + `docker-compose environment:` (container-internal constants only). Kill custom config loader. Eliminate all duplication.

## Outcome

Implementation took a **pragmatic subset** approach — solved the highest-value problems (duplication, discoverability, docs) without the per-service env file split or loader removal. See commit `d0a4da3`.

### What was done
- `.env.example` reorganized: sectioned layout, commented defaults pattern (duplication eliminated at template level)
- `docker-compose.yml` cleaned: removed redundant `DAGSTER_HOME`, `BACKUP_KEEP_COUNT`; consistent config mounts
- `docs/config-guide.md` created: documents all 5 config layers, precedence, conventions
- `backup.sh` fixed: pipefail exit code 2 on empty glob, consistent PROJECT_ROOT
- `utils.py` updated: load `.env.local` from project root (not `ingestion/`)
- Data-pipeline skill updated (L35, troubleshooting, template)

### What was deferred (low ROI for now)
- **Phase 1** (per-service env split): single `.env.docker` works fine; split adds operational overhead for 2-service setup
- **Phase 3** (kill config loader): `load_dlt_configuration()` still needed for local dev without Docker; removal requires Docker-only workflow

## Phases

| # | Phase | File | Status | Effort |
|---|-------|------|--------|--------|
| 1 | Split .env.docker into per-service files | [phase-01](phase-01-split-env-files.md) | Rejected | — |
| 2 | Deduplicate config.toml vs .env | [phase-02](phase-02-deduplicate-config.md) | Done | — |
| 3 | Kill custom config loader | [phase-03](phase-03-kill-config-loader.md) | Rejected | — |
| 4 | Clean docker-compose environment block | [phase-04](phase-04-clean-compose-env.md) | Done | — |
| 5 | Update .env.example + docs | [phase-05](phase-05-update-templates.md) | Done | — |
| 6 | Validate & smoke test | [phase-06](phase-06-validate.md) | Done (deployed, running) | — |

## Dependency Graph
```
Phase 1 (split env files)
  └─> Phase 2 (deduplicate) — needs new file structure
       └─> Phase 3 (kill loader) — needs clean env resolution
            └─> Phase 4 (clean compose env) — needs loader gone
                 └─> Phase 5 (update templates) — needs final state
                      └─> Phase 6 (validate) — needs everything done
```

## Rollback
All phases are file edits only. Rollback = `git checkout -- .` + restore `.env.docker` from backup. Docker containers unaffected until explicit `docker compose up -d --force-recreate`.

## Key Design Decisions
1. **3 env files**: `.env.data-platform.docker`, `.env.metabase.docker`, `.env.shared.docker` (TZ only)
2. **config.toml stays committed** — it holds dlt defaults (layout, format, selectors), not secrets
3. **DESTINATION__FILESYSTEM__*** vars removed from .env — they live in config.toml already; env override available but commented out
4. **load_dlt_configuration() deleted** — docker-compose `env_file:` injects vars; dlt reads config.toml natively; no manual loading needed
5. **Sheets URLs** — single source in config.toml, sensor reads via `dlt.config["sources.spreadsheet_url.targets"]` or env var override

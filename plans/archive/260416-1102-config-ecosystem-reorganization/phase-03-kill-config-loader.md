# Phase 3: Kill Custom Config Loader

## Context
- [orchestration/assets/utils.py](../../orchestration/assets/utils.py) — the 129-line loader to eliminate
- [phase-02](phase-02-deduplicate-config.md) — prerequisite
- [plan.md](plan.md)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Effort**: 45m
- **Blocked by**: Phase 2

## Problem
`load_dlt_configuration()` in `orchestration/assets/utils.py` is 129 lines of hand-rolled .env and TOML parsing that:
1. Loads `ingestion/.env.local` into `os.environ` (hand-rolled parser with inline comment handling)
2. Loads `ingestion/.dlt/secrets.toml` into `os.environ` (flattens TOML sections to `__`-separated env vars)
3. Is called at the top of EVERY asset function (11 call sites across 5 asset files)

**Why it existed**: Dagster doesn't auto-load `.env.local` or `secrets.toml` — the loader bridged this gap manually.

**Why it's now unnecessary**: After Phase 1-2, all env vars are injected by `docker-compose env_file:` directives. Inside the container, `os.environ` already has everything. dlt reads `config.toml` and `secrets.toml` natively when `os.chdir(DLT_DIR)` is called (dlt resolves `.dlt/` relative to cwd).

## Architecture

### What load_dlt_configuration() Currently Does

```
1. Parse ingestion/.env.local → os.environ    # REPLACED by docker-compose env_file
2. Parse ingestion/.dlt/secrets.toml → os.environ  # REPLACED by dlt native resolution
3. Verify SOURCES__SAPO__DOMAIN + USERNAME present  # Can be a simple assert
```

### Replacement Strategy

**Docker environment**: `env_file:` in docker-compose injects all vars. dlt reads `secrets.toml` natively. Nothing to do.

**Local dev environment** (running outside Docker): `.env.local` is still useful. But instead of a custom parser, use `python-dotenv` (already a transitive dep via dlt) or just document "source .env.local before running".

### Changes to utils.py

Replace `load_dlt_configuration()` with a minimal verification function:

```python
def verify_dlt_config(log_func=print):
    """Verify critical dlt config vars are present in environment.
    
    In Docker: vars come from env_file directives in docker-compose.yml.
    Locally: vars come from .env.local (loaded by python-dotenv or shell).
    dlt reads config.toml + secrets.toml natively from cwd/.dlt/.
    """
    missing = []
    for var in ("SOURCES__SAPO__DOMAIN", "SOURCES__SAPO__USERNAME"):
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        log_func(f"[Config] WARNING: Missing env vars: {', '.join(missing)}. "
                 f"Check .env.data-platform.docker or secrets.toml.")
    else:
        log_func("[Config] Verified: Sapo credentials present in environment.")
```

### Call Site Changes

All 11 call sites follow the same pattern:
```python
# BEFORE
load_dlt_configuration(context.log.info)

# AFTER
verify_dlt_config(context.log.info)
```

This is a pure rename/simplify — no behavioral change for Docker runs.

## Callers (11 sites in 5 files)

| File | Line(s) | Count |
|------|---------|-------|
| `orchestration/assets/sapo_assets.py` | 55, 106, 156, 207, 254, 301 | 6 |
| `orchestration/assets/sheets_assets.py` | 36, 83 | 2 |
| `orchestration/assets/shopee_assets.py` | 55 | 1 |
| `orchestration/assets/misa_amis_assets.py` | 55 | 1 |
| `.skills/data-pipeline/templates/dagster-asset-template.py` | 61 | 1 (template) |

## Related Code Files
- **Modify**: `orchestration/assets/utils.py` — replace `load_dlt_configuration` with `verify_dlt_config`
- **Modify**: `orchestration/assets/sapo_assets.py` — update 6 call sites
- **Modify**: `orchestration/assets/sheets_assets.py` — update 2 call sites
- **Modify**: `orchestration/assets/shopee_assets.py` — update 1 call site
- **Modify**: `orchestration/assets/misa_amis_assets.py` — update 1 call site
- **Modify**: `.skills/data-pipeline/templates/dagster-asset-template.py` — update template
- **Modify**: `.skills/data-pipeline/dagster-patterns.md` — update pattern docs
- **Modify**: `.skills/data-pipeline/lessons-learned.md` — update L10 lesson
- **No change**: `ingestion/.dlt/secrets.toml` — dlt reads it natively, no code needed

## Implementation Steps

1. In `orchestration/assets/utils.py`:
   - Delete `load_dlt_configuration()` function (lines 12-129)
   - Add `verify_dlt_config()` (~15 lines)
   - Keep `DLT_DIR` and `CURRENT_DIR` exports (other files use them)
2. In all 5 asset files: replace `load_dlt_configuration` import and calls with `verify_dlt_config`
3. Update skill template + docs to reference new function name
4. Verify `os.chdir(DLT_DIR)` still happens before pipeline runs (this is what makes dlt find `.dlt/config.toml` and `.dlt/secrets.toml` — must NOT be removed)

## Key Insight: os.chdir(DLT_DIR) is Critical

Every asset does `os.chdir(DLT_DIR)` before running the dlt pipeline. This sets the working directory to `ingestion/`, which is where `.dlt/config.toml` and `.dlt/secrets.toml` live. dlt's native config resolution finds them relative to cwd. **Do not remove os.chdir(DLT_DIR).**

## Todo
- [ ] Replace load_dlt_configuration with verify_dlt_config in utils.py
- [ ] Update sapo_assets.py (6 call sites)
- [ ] Update sheets_assets.py (2 call sites)
- [ ] Update shopee_assets.py (1 call site)
- [ ] Update misa_amis_assets.py (1 call site)
- [ ] Update skill template
- [ ] Update lessons-learned.md and dagster-patterns.md
- [ ] Verify os.chdir(DLT_DIR) preserved in all assets

## Success Criteria
- `grep -r "load_dlt_configuration" orchestration/` returns 0 matches
- `utils.py` is under 30 lines (down from 129)
- All assets still run successfully in Docker (Sapo credentials resolve from env)
- dlt still reads config.toml defaults (layout, format) via native resolution

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| secrets.toml not found by dlt | Low | High | `os.chdir(DLT_DIR)` already sets cwd; dlt resolution tested for years |
| Local dev breaks (.env.local no longer auto-loaded) | Medium | Low | Document: run `set -a; source ingestion/.env.local; set +a` before local dev. Single-dev project, minor friction. |
| Asset template in skills outdated | Low | Low | Update in same phase |

## Backwards Compatibility
- **Docker**: Zero change — env vars still injected, dlt still reads config.toml
- **Local dev**: Breaking change — must manually source .env.local or use `python-dotenv`. Acceptable for single-dev project. Document in .env.example header.

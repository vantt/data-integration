# Phase 2: Deduplicate config.toml vs .env

## Context
- [config.toml](../../ingestion/.dlt/config.toml) — dlt defaults (committed)
- [phase-01](phase-01-split-env-files.md) — prerequisite
- [plan.md](plan.md)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Effort**: 30m
- **Blocked by**: Phase 1

## Problem
Same values defined in 3 places simultaneously:
1. `DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT=parquet` in .env.docker + config.toml + .env.example
2. `DESTINATION__FILESYSTEM__LAYOUT=...` in .env.docker + config.toml + .env.example
3. `DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS=...` in .env.docker + config.toml + .env.example
4. Sheets URLs in config.toml `[sources.spreadsheet_url]` + sensor hardcoded defaults

### Single Source of Truth Rule
| Variable | Owner | Reason |
|----------|-------|--------|
| `loader_file_format`, `layout`, `extra_placeholders` | **config.toml** | dlt-native config, rarely changes, not a secret |
| `bucket_url` | **.env.data-platform.docker** | path differs per environment (Docker vs local) |
| `domain`, `request_delay`, `headless`, `login_*` | **config.toml** | dlt defaults, not secrets |
| `username`, `password` | **secrets.toml / .env** | actual credentials |
| Sheets URLs | **config.toml** `[sources.spreadsheet_url]` | public URLs, not secrets |

## Architecture

### What Gets Removed from .env

Remove from `.env.data-platform.docker` (created in Phase 1):
```
# REMOVE — owned by config.toml:
DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT  (= parquet)
DESTINATION__FILESYSTEM__LAYOUT              (= {table_name}/...)
DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS  (= {"ingest_method":...})
```

Keep in `.env.data-platform.docker`:
```
DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/data_lake   # env-specific path
```

### Sheets URL Deduplication

**Current state** (3 places):
1. `config.toml` `[sources.spreadsheet_url]` — the canonical URLs
2. `sheets_modified_sensor.py` lines 45-52 — hardcoded `_DEFAULT_*_URL` constants
3. Env var override: `SHEETS_SENSOR_TARGETS_URL`, `SHEETS_SENSOR_MARKETING_URL`

**Target state** (1 place + override):
1. `config.toml` `[sources.spreadsheet_url]` — single source of truth
2. Sensor reads URLs from env vars `SHEETS_SENSOR_TARGETS_URL` / `SHEETS_SENSOR_MARKETING_URL`
3. If env vars not set, sensor reads from config.toml via `dlt.config` or a tiny helper
4. No more hardcoded URL constants in sensor code

**Pragmatic approach**: Since the sensor runs at module import time (Dagster loads it), reading config.toml via `tomllib` is simplest. Keep env var override for flexibility.

```python
# sheets_modified_sensor.py — replace hardcoded URLs
import tomllib
from pathlib import Path

_CONFIG_TOML = Path(__file__).resolve().parents[2] / "ingestion" / ".dlt" / "config.toml"

def _load_sheet_urls() -> dict[str, str]:
    """Read sheet URLs from config.toml, allow env override."""
    urls = {}
    if _CONFIG_TOML.exists():
        with open(_CONFIG_TOML, "rb") as f:
            cfg = tomllib.load(f)
        sheet_cfg = cfg.get("sources", {}).get("spreadsheet_url", {})
        urls["targets"] = sheet_cfg.get("targets", "")
        urls["marketing_spend"] = sheet_cfg.get("marketing_spend", "")
    # Env var override (convert edit URL → CSV export URL if needed)
    urls["targets"] = os.environ.get("SHEETS_SENSOR_TARGETS_URL", urls.get("targets", ""))
    urls["marketing_spend"] = os.environ.get("SHEETS_SENSOR_MARKETING_URL", urls.get("marketing_spend", ""))
    return urls
```

**Note**: config.toml has edit URLs, sensor needs CSV export URLs. Two options:
- A) Store export URLs in config.toml (add `_export_csv` keys) — cleanest
- B) Transform edit URL → export URL in sensor code — fragile

Recommend **option A**: add export URL keys to config.toml under `[sources.spreadsheet_url]`.

## Related Code Files
- **Modify**: `.env.data-platform.docker` — remove 3 DESTINATION vars
- **Modify**: `orchestration/sensors/sheets_modified_sensor.py` — replace hardcoded URLs
- **Modify**: `ingestion/.dlt/config.toml` — add CSV export URL keys
- **Modify**: `.env.example` — remove duplicated DESTINATION vars, add commented-out overrides

## Implementation Steps

1. Remove `DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT`, `LAYOUT`, `EXTRA_PLACEHOLDERS` from `.env.data-platform.docker`
2. Add CSV export URL keys to config.toml:
   ```toml
   [sources.spreadsheet_url]
   marketing_spend = "https://docs.google.com/spreadsheets/d/1wQpT4lCZWrPE7fnbRNTKiNDRFzVT2u_WhN-9uY9u3lc/edit?usp=sharing"
   marketing_spend_csv = "https://docs.google.com/spreadsheets/d/1wQpT4lCZWrPE7fnbRNTKiNDRFzVT2u_WhN-9uY9u3lc/export?format=csv"
   targets = "https://docs.google.com/spreadsheets/d/1ZHt2iAD88OGgSRopVOkqEgusja-JpP4XqtiH4anhax4/edit?usp=sharing"
   targets_csv = "https://docs.google.com/spreadsheets/d/1ZHt2iAD88OGgSRopVOkqEgusja-JpP4XqtiH4anhax4/export?format=csv"
   ```
3. Refactor `sheets_modified_sensor.py`:
   - Remove `_DEFAULT_TARGETS_URL` and `_DEFAULT_MARKETING_URL` constants
   - Add `_load_sheet_urls()` helper reading from config.toml with env override
   - Replace `SHEET_URLS` dict initialization
4. Verify `ingestion/src/utils/pipeline_runner.py` commented-out lines stay commented (already done)

## Todo
- [ ] Remove 3 DESTINATION__FILESYSTEM vars from .env.data-platform.docker
- [ ] Add CSV export URL keys to config.toml
- [ ] Refactor sheets_modified_sensor.py to read from config.toml
- [ ] Remove duplicated DESTINATION vars from .env.example (Phase 5 finalizes)
- [ ] Test: dlt pipeline still picks up layout/format from config.toml

## Success Criteria
- `DESTINATION__FILESYSTEM__LAYOUT` appears in exactly 1 place: config.toml
- Sheets URLs appear in exactly 1 place: config.toml (with env override available)
- `grep -r "DESTINATION__FILESYSTEM__LAYOUT" --include="*.env*"` returns nothing

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| dlt ignores config.toml when env var is set | Low | High | This is dlt's native behavior — env always wins. We're removing env so config.toml takes effect |
| Sensor fails to read config.toml path | Low | Medium | Use `__file__`-relative path; add fallback log warning |
| CSV export URL format changes | Very Low | Low | Env override available as escape hatch |

## Security
- No secrets involved — layout/format/URLs are all public config
- CSV export URLs are already public (anyone with link)

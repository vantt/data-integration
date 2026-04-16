# Project Changelog

> Record of significant changes, features, and fixes

## [2026-04-16] Docker Volume Restructure

**Summary:** Reorganized Docker volume mounts from flat `/app/` to grouped `/app/var/` for data directories.

**Changes:**

| Before | After | Type |
|--------|-------|------|
| `/app/data_lake` | `/app/var/data_lake` | Data dir |
| `/app/.dagster_home` | `/app/var/dagster_home` | Data dir |
| `/app/logs` | `/app/var/logs` | Data dir |
| `/app/backups` | `/app/var/backups` | Data dir |
| (not mounted) | `/app/var/input_source` | Data dir (NEW) |
| `/app/transformation`, `/app/ingestion`, `/app/orchestration`, `/app/scripts` | (unchanged) | Code dirs |

**Local Host Bind:**
```
app_data/data_lake       →  /app/var/data_lake
app_data/dagster_home    →  /app/var/dagster_home
app_data/logs            →  /app/var/logs
app_data/backups         →  /app/var/backups
app_data/input_source    →  /app/var/input_source
```

**Env Var Updates:**

```bash
# .env.docker now uses:
DBT_DATA_LAKE_PATH=/app/var/data_lake
DBT_EXPORT_PATH=/app/var/data_lake/export/marts
DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/var/data_lake
BACKUP_ROOT=/app/var/backups
DAGSTER_HOME=/app/var/dagster_home
SHOPEE_INPUT_DIR=/app/var/input_source/shopee
```

**Critical Impact:**

- **Serving views bake absolute paths** — After mount changes, must regenerate:
  ```bash
  docker compose down
  docker compose up -d data_platform
  docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
  docker compose up -d metabase
  ```

**Benefits:**

1. Clear separation: code at `/app/`, data at `/app/var/`
2. Simpler volume management in docker-compose.yml
3. Easier to identify data vs code directories at glance
4. File drop input_source now mounted (enables auto-trigger sensors)

**Documentation Updated:**

- `docs/architecture/overview.md` — Docker deployment topology
- `docs/operations/deployment.md` — Volume mount references + serving views regeneration
- `.skills/data-pipeline/SKILL.md` — Docker volume convention + critical serving views note

---

## Future Changelog Entries

Add new entries in reverse chronological order (newest first) using this template:

```markdown
## [YYYY-MM-DD] Feature/Fix Title

**Summary:** One-line description

**Changes:**
- List of changes
- Document any breaking changes

**Impact:**
- Documentation files updated
- Code files modified
```

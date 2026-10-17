# Scout: orchestration, ingestion, deploy (condensed)

Read-only scouting on 2026-10-13. The subagent returned findings inline; this file keeps the facts the plan depends on.

## Orchestration wiring

- `orchestration/definitions.py` (835 lines) is pure wiring: `sys.path` hacks (L6-7), `load_assets_from_modules([...13 modules...])` (L47), one dbt selection for the whole graph (L69), `SYNC_TAGS = {"concurrency_group": "dbt_rw"}` (L78), per-source jobs (L81-268), schedules with self-overlap guard `_has_active_run` (L294, L372-750), `trigger_backup_after_purge` sensor (L556-577), single `DbtCliResource` (L829-833), `Definitions(...)` (L757-835).
- Cross-source job: `_fact_order_returns` (L137) is pulled into both the Shopee and the MISA file-drop jobs.
- `orchestration/assets/dbt.py`: `@dbt_assets` (L94) has no `select=`, so every dbt model is one asset group. `SapoDbtTranslator` (L30-89) maps each dbt source to a Dagster asset key by hand. Op concurrency key `duckdb_lock` (L98).
- `orchestration/assets/serving.py` runs `scripts/provisioning/refresh_rolling.py` + `bootstrap_serving_views.py`; the served table set is discovered from `rolling/<name>/` folders, not from a list.
- Ingestion is invoked three ways: module import (Sapo, Sheets, Hug), `importlib` of hyphenated files (Shopee, MISA), subprocess (serving, rill, dbt GC, approach scripts).

## Source membership is spread across these files

| File | What is source-specific |
|---|---|
| `orchestration/definitions.py` | job selections and schedules per source |
| `orchestration/asset_checks/__init__.py` L28-53 | hardcoded import of 5 asset modules to build the asset-def map |
| `orchestration/asset_checks/reconciliation_checks.py` L156-159 | recon asset keys for Shopee, MISA, Sapo |
| `orchestration/ops/morning_digest.py` L31-74 | `KNOWN_ASSETS` and Vietnamese display labels per source |
| `orchestration/sensors/stuck_run_alerter.py` L70-78 | `_JOB_MAX_RUNTIME` per job |
| `orchestration/sensors/file_drop_sensors.py` L37-190 | drop dirs, job names, op names |
| `orchestration/sensors/sheets_modified_sensor.py` L45-70 | sheet URLs |
| `orchestration/config/ingestion_sla.yaml` | keys = `<key_prefix>/<function_name>`; a rename silently drops checks |
| `orchestration/assets/dbt.py` L30-89 | dbt source → asset key mapping |
| `transformation/models/sources.yml` | dataset names and parquet globs per source |
| `ingestion/.dlt/config.toml` L10-44 | per-source config sections |

## Generic (kernel) candidates

`sensors/failure_alerting.py`, `sensors/concurrency_pool_janitor.py`, `sensors/health_db_watchdog_sensor.py`, `ops/system_backup.py`, `ops/purge_runs.py`, `ops/ingestion_health.py`, `ops/dlt_metrics.py`, `ops/file_metrics.py`, `asset_checks/{health_db,freshness_checks,row_trend_checks,cursor_checks,sla_loader}.py`, `notifications/lark_client.py`, `assets/serving.py`, `assets/dbt.py` (once the translator is data-driven), `ingestion/src/utils/pipeline_runner.py`, `ingestion/src/file-drop-utils.py`.

## Notification wiring

`orchestration/notifications/lark_client.py` exposes `send_lark_card` (L43, env `LARK_ALERT_WEBHOOK`). Direct importers: `ops/purge_runs.py:11`, `sensors/failure_alerting.py:12`, `sensors/stuck_run_alerter.py:29`, `sensors/health_db_watchdog_sensor.py:22`, `ops/system_backup.py:18`, `ops/morning_digest.py:24`.

## Cross-component imports

- **Live bug:** `crm/ops/backup_crm.py:254-258` imports `orchestration.notifications.lark_client.send_lark_alert`, which does not exist; the error is swallowed by `except Exception: pass`, so CRM backup alerts are never sent.
- `scripts/maintenance/{cleanup_dbt_target_dirs_standalone,backfill_ingestion_health_rows_written,purge_dagster_runs}.py` import `orchestration.ops.*` (ops scripts, acceptable as kernel tooling).
- Network/file coupling: orchestration → `crm:8090` HTTP (`crm_sync.py`, `approach_script_generation.py`); `crm_writeback_assets.py` reads CRM SQLite; `sheets_assets.py:271` writes dbt seed CSVs.

## Ingestion

- Entry scripts: Sapo 7 (`run_sapo_v2_*`), Hug 1, Shopee 1, MISA 6 (hyphenated), Google Sheets via `src/gsheet_*`, Facebook 2 (`run_facebook_ads_batch.py`, `run_facebook_messenger_batch.py`).
- **Facebook ingestion has no Dagster asset or schedule** (orphaned in orchestration).
- `pipeline_runner.run_pipeline` defaults `dataset_name="sapo_v2_raw"`.
- Config mismatch: `.dlt/config.toml` MISA `input_dir` = `misa-amis`; assets/sensors use `misa-sales-ledger`.

## Deploy

- `Dockerfile.dataplatform` copies ingestion, transformation, orchestration, webhook_consumer, scripts; CMD `dagster dev -f orchestration/definitions.py`; no `workspace.yaml`.
- `docker-compose.yml` bind-mounts host code into `data_platform` (L28-32): **editing files on the prod checkout changes prod immediately.**
- Path env vars: `DBT_DATA_LAKE_PATH`, `DBT_EXPORT_PATH`, `INGESTION_HEALTH_DB`, `CRM_DB_PATH`, `SHOPEE_INPUT_DIR`, `MISA_INPUT_DIR`, `MISA_ACCOUNT_LEDGER_INPUT_DIR`, `DESTINATION__FILESYSTEM__BUCKET_URL`, `LARK_ALERT_WEBHOOK`, and others in `.env.docker`.

## Tests

Root `conftest.py` sets temp `DBT_DATA_LAKE_PATH`/`INGESTION_HEALTH_DB`. Tests: `ingestion/tests/` (2), `orchestration/**/__tests__/` (5), `scripts/tests/` (4). Suggested: `python -m pytest ingestion/tests orchestration scripts/tests -q` (inside the data_platform image).

## Plan 260705-1704 status

DRAFT, zero phases executed; no import-linter config exists; `crm/ops/lark_alert.py` does not exist.

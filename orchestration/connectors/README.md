# Connector packages

One package per data source under `orchestration/connectors/<id>/`. The kernel (`definitions.py`, `ops/`, `sensors/`, `asset_checks/`, `assets/dbt.py`) knows connectors only through the packages listed in [`../config/modules.yaml`](../config/modules.yaml). Architecture and write authority: [docs/architecture/modules.md §4–§5](../../docs/architecture/modules.md).

Enabled today: `sapo_v2`, `shopee`, `misa_amis`, `sheets`, `hug` (`hug` feeds the `hug` pack). Facebook ingestion has no Dagster asset yet and is noted as dormant in `modules.yaml`. Packs (`orchestration/packs/`, [README](../packs/README.md)) and the tenant (`orchestration/tenants/`) are listed in the same file and loaded the same way (`orchestration/module_registry.py`).

## Contract

Each package is plain Python exporting lists and dicts — no base class, no registry object.

`<id>/__init__.py` (light: imports its `assets.py`, never `assets/dbt.py`):

| Export | Type | Consumed by |
|---|---|---|
| `ASSETS` | `list` of asset definitions | `definitions.py` (Definitions assets) |
| `CHECK_ASSET_DEFS` | `dict[str, AssetsDefinition \| AssetKey]`, key = SLA key `<prefix>/<function_name>` | `asset_checks/__init__.py` builds freshness / not-empty / trend / cursor checks for every SLA key that has an entry |
| `NIGHTLY_ASSETS` | `list` of ingest assets | the cross-source `pipeline_batch_nightly_job` and `pipeline_batch_fullrefresh_job` in `definitions.py` |
| `DIGEST_ASSETS` | `list[tuple[short_name, sla_key, recon_sla_key \| None]]` | `ops/morning_digest.py` `KNOWN_ASSETS` |
| `DIGEST_DISPLAY` | `dict[short_name, tuple[label, asset_type, unit]]` (`asset_type` ∈ cursor, batch, file_drop) | `morning_digest.ASSET_DISPLAY` |
| `JOB_MAX_RUNTIME` | `dict[job_name, timedelta]` | `sensors/stuck_run_alerter.py` (absolute max runtime; unlisted jobs get 90 min) |
| `DBT_SOURCE_KEYS` | `dict[dbt source_name, dict[table, AssetKey]]`; table `"*"` = any other table | `SapoDbtTranslator` in `assets/dbt.py`: dbt sources the connector ingests map to its ingest asset keys; other sources keep the dbt default |

`<id>/jobs.py` (heavy: selects the dbt assets, so it imports `assets/dbt.py`):

| Export | Type |
|---|---|
| `JOBS` | `list` of jobs (`define_asset_job`) |
| `SCHEDULES` | `list` of schedules |
| `SENSORS` | `list` of sensors |

`jobs.py` is separate from `__init__.py` because `assets/dbt.py` reads `DBT_SOURCE_KEYS` from the packages while jobs need `dbt.sapo_dbt_assets`; one module doing both would be an import cycle. `orchestration.connectors` exposes `enabled_ids()`, `load_enabled()` (the packages) and `load_enabled_jobs()` (their `jobs` modules).

Jobs that span sources (`pipeline_batch_nightly_job`, `pipeline_batch_fullrefresh_job`) stay in `definitions.py` and select `NIGHTLY_ASSETS` of every enabled connector.

## Rules

- Names are the identity of live state: asset keys, asset check keys, job, schedule and sensor names, cron, timezone and default status must not change when code moves. Schedule on/off state in `dagster_home` is keyed by code location, repository and name.
- Connectors import from the kernel (`orchestration.assets.utils`, `orchestration.ops.*`, `orchestration.job_support`, `orchestration.sensors.file_drop_sensors`), never the reverse except through `load_enabled()`.
- Connectors do not import packs (`check_boundaries.py`, rule `orch-import`; no allowlist entry). A sync job that rebuilds serving ends with `| after_serving_selection()` from `orchestration.job_support`: the kernel adds the `AFTER_SERVING_ASSETS` of the enabled packs (today the crm pack's `crm_cache_refresh`), or nothing when no enabled pack declares any. The jobs of `sapo_v2` (realtime, incremental), `shopee`, `misa_amis` (two file-drop jobs) and `sheets` do this.
- Paths come from `DLT_DIR` (`orchestration/assets/utils.py`), not from `__file__`, so a package can move without breaking ingestion script imports.
- No hard-coded `http(s)://` URL, and no domain name in a string literal, in this tree (`scripts/checks/check_boundaries.py`, rule `connector-url`); tenant values live in `orchestration/tenants/<tenant>/config.py` and are read with `orchestration.tenants.setting(name)`, which fails closed when the value is missing (the `sheets` connector's `ingest_sheets_modified_sensor` reads its sheet URLs this way).
- One SLA file: `config/ingestion_sla.yaml`.

## Add a connector

1. `orchestration/connectors/<id>/assets.py` with the assets; ingestion scripts stay in `ingestion/`.
2. `__init__.py` exporting the seven names above; `jobs.py` exporting `JOBS`, `SCHEDULES`, `SENSORS` (empty lists are fine). Reuse `make_file_drop_sensor` (`sensors/file_drop_sensors.py`) for Excel drop zones and `job_support.has_active_run` for schedule overlap checks.
3. SLA entries in `config/ingestion_sla.yaml` for the keys in `CHECK_ASSET_DEFS`.
4. Add the id to `config/modules.yaml`, restart the code server.
5. dbt side: `transformation/models/connectors/<id>/` (see `docs/architecture/modules.md` §2b).

## Drop a connector

Remove its id from `config/modules.yaml` and restart. Its assets, jobs, schedules, sensors, asset checks and digest rows disappear; nothing else changes (SLA entries left in the YAML log a warning and are skipped). Verified in the shadow environment for `hug`: only its asset, job, schedule and two checks were removed from the inventory. The cross-source jobs keep working because they read `NIGHTLY_ASSETS` from whatever is enabled; dbt assets that depend on a dropped connector's source simply lose that upstream edge.

## Verify a change

```bash
scripts/shadow/gate.sh M          # Dagster inventory must show 0 differences
scripts/shadow/pytest-shadow.sh $PWD lake-A orchestration -q
python3 scripts/checks/check_boundaries.py --manifest <dbt manifest.json>
```

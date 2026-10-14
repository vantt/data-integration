# Pack packages

One package per product pack under `orchestration/packs/<id>/`. A pack is reusable product logic (CRM, HUG, finance, sales playbook) that runs on the data the connectors bring in; the business (tenant) only supplies data and configuration. The kernel (`definitions.py`) knows packs only through the ids listed under `packs:` in [`../config/modules.yaml`](../config/modules.yaml). Architecture: [docs/architecture/modules.md §8](../../docs/architecture/modules.md).

Enabled today: `crm`, `hug`, `finance`, `sales_playbook`. The dbt side of each pack lives in `transformation/models/packs/<id>/` (each with a README).

## Contract

Plain Python exporting lists — no base class, no registry object.

| File | Export | Consumed by |
|---|---|---|
| `<id>/__init__.py` | `ASSETS` (list of asset definitions) | `definitions.py` (Definitions assets) |
| `<id>/__init__.py` | `NIGHTLY_ASSETS` (subset of `ASSETS`) | `pipeline_batch_nightly_job` and `pipeline_batch_fullrefresh_job` |
| `<id>/jobs.py` | `JOBS`, `SCHEDULES`, `SENSORS` | `definitions.py` |

A pack with no Dagster code of its own (`hug`, `finance`: their models run inside the kernel's dbt assets) exports empty lists, so the enabled packs match the dbt side. `orchestration.packs` exposes `enabled_ids()`, `load_enabled()` and `load_enabled_jobs()` (same loader as connectors: `orchestration/module_registry.py`).

| Pack | Assets | Job (schedule) | README |
|---|---|---|---|
| `crm` | `crm_cache_refresh` (group `reporting_layer`), 11 `crm_*_export` (group `crm_writeback`), `crm_backup`, `crm_restore_verify` (group `ops_maintenance`) | `crm_backup_job` (`crm_backup_schedule`, 02:00) | [crm/README.md](crm/README.md) |
| `sales_playbook` | `approach_script_autogen` (group `approach_script_autogen`) | — | [sales_playbook/README.md](sales_playbook/README.md) |
| `hug` | — | — | [hug/README.md](hug/README.md) |
| `finance` | — | — | [finance/README.md](finance/README.md) |

## Rules

- Names are the identity of live state: asset keys, groups, job, schedule and sensor names, cron and default status do not change when code moves.
- Packs import from the kernel (`orchestration.assets.*`, `orchestration.job_support`, `orchestration.tenants.setting`), never from a connector.
- A pack does not import another pack and a connector does not import a pack (`check_boundaries.py`, rule `orch-import`). Known couplings are allowlisted per file: the four connector jobs that select `crm_cache_refresh`, and `sales_playbook` running after `crm_cache_refresh`. Exit after Đợt 1.
- No hard-coded `http(s)://` URL or domain in this tree (rule `pack-url`). Endpoints are tenant settings: `orchestration.tenants.setting("<NAME>")` reads the env var `<NAME>` or `orchestration/tenants/<tenant>/config.py`, and fails with `TenantConfigError` when neither has it.

## Turning a pack off

Not supported yet. Connector jobs still select `crm_cache_refresh`, and core dbt models read pack models (pack hooks in `scripts/checks/boundary_allowlist.yaml`). The `pack_ref` macro and the `enabled_packs` dbt variable come after Đợt 1 (`plans/261013-1751-modularize-data-platform-suite/roadmap.md`, "Cơ chế pack").

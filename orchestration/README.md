# Orchestration Layer

Pipeline scheduling and coordination using [Dagster](https://dagster.io/).

Manages job schedules, asset dependencies, and concurrency control for the full data pipeline.

## Documentation

Full documentation is in [docs/](./docs/README.md):

- [Jobs](./docs/JOBS.md) — Job definitions and configurations
- [Assets](./docs/ASSETS.md) — Asset dependency graph
- [Schedules](./docs/SCHEDULES.md) — Schedule definitions and conflict resolution
- [Resources](./docs/RESOURCES.md) — Dagster resources

## Layout: kernel, connectors, packs, tenant

| Path | Role |
|---|---|
| `definitions.py` | Kernel entry point. Merges the kernel assets with every connector and pack listed in `config/modules.yaml`; defines the cross-source jobs (nightly batch, full refresh), health and maintenance jobs and their schedules |
| `config/modules.yaml` | Enabled connectors (in digest order), packs and the tenant; read by `module_registry.py` |
| `config/ingestion_sla.yaml` | The one SLA file (freshness, trend, cursor thresholds) keyed `<prefix>/<function_name>`; a missing file raises |
| `connectors/<id>/` | One package per data source: its ingest assets, jobs, schedules, sensors and the data the kernel needs about it. Contract and how to add or drop one: [connectors/README.md](./connectors/README.md) |
| `packs/<id>/` | Product packs (`crm`, `hug`, `finance`, `sales_playbook`): Dagster code of reusable product logic. `crm` owns the CRM write-back, cache refresh and `crm_backup_job`; `sales_playbook` owns the approach-script autogen; `hug` and `finance` have no Dagster code. Contract: [packs/README.md](./packs/README.md) |
| `tenants/<id>/config.py` | Configuration of the business this deployment runs for (Fine Japan: [tenants/fine_japan/README.md](./tenants/fine_japan/README.md)), read through `orchestration.tenants.setting(name)`; shared code has no default for these values. Google Sheet URLs are not here: they come only from `SOURCES__SPREADSHEET_URL__<NAME>` (shared by the `ingestion/src/gsheet_*.py` readers and `sensors/sheets_modified_sensor.py`) |
| `job_support.py` | `SYNC_TAGS`, `has_active_run`, `long_dbt_rw_holder` used by connector schedules |
| `assets/{dbt,serving,rill,reconciliation,kpi_closure}.py`, `sensors/`, `ops/`, `asset_checks/`, `notifications/` | Kernel, generic for every source. They keep their location on purpose: several compute paths from `__file__` |

The kernel never imports a connector, pack or tenant by name; it reads the enabled packages through `orchestration.connectors.load_enabled()`, `orchestration.packs.load_enabled()` and `orchestration.tenants.setting()`. The rules (no connector → pack import, no URL in connectors or packs, ingestion never imports orchestration) are enforced by `scripts/checks/check_boundaries.py`; design and decisions: [docs/architecture/modules.md](../docs/architecture/modules.md), [ADR-015](../docs/decisions/015-module-boundaries.md), [ADR-017](../docs/decisions/017-packs-and-tenants.md).

Before committing a change here, run `scripts/checks/run-all.sh` from the repository root of your worktree (dbt parse, boundaries, `dagster definitions validate`, pytest).

## Quick Start

```bash
# Start Dagster UI (development)
dagster dev

# Validate definitions
dagster definitions validate

# Execute a job manually
dagster job execute -j pipeline_batch_nightly_job
```

→ See [System Architecture](../docs/architecture/overview.md) for how orchestration fits into the full pipeline.

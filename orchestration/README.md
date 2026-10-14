# Orchestration Layer

Pipeline scheduling and coordination using [Dagster](https://dagster.io/).

Manages job schedules, asset dependencies, and concurrency control for the full data pipeline.

## Documentation

Full documentation is in [docs/](./docs/README.md):

- [Jobs](./docs/JOBS.md) — Job definitions and configurations
- [Assets](./docs/ASSETS.md) — Asset dependency graph
- [Schedules](./docs/SCHEDULES.md) — Schedule definitions and conflict resolution
- [Resources](./docs/RESOURCES.md) — Dagster resources

## Layout: kernel and connectors

| Path | Role |
|---|---|
| `definitions.py` | Kernel entry point. Merges the kernel assets with every connector listed in `config/modules.yaml`; defines the cross-source jobs (nightly batch, full refresh), health, maintenance and CRM backup jobs and their schedules |
| `config/modules.yaml` | Enabled connectors, in digest order |
| `config/ingestion_sla.yaml` | The one SLA file (freshness, trend, cursor thresholds) keyed `<prefix>/<function_name>`; a missing file raises |
| `connectors/<id>/` | One package per data source: its ingest assets, jobs, schedules, sensors and the data the kernel needs about it. Contract and how to add or drop one: [connectors/README.md](./connectors/README.md) |
| `job_support.py` | `SYNC_TAGS`, `has_active_run`, `long_dbt_rw_holder` used by connector schedules |
| `assets/{dbt,serving,rill,reconciliation,kpi_closure}.py`, `sensors/`, `ops/`, `asset_checks/`, `notifications/` | Kernel, generic for every source. They keep their location on purpose: several compute paths from `__file__` |

The kernel never imports a connector by name; it reads the enabled packages through `orchestration.connectors.load_enabled()`.

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

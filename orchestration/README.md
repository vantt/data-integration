# Orchestration Layer

Pipeline scheduling and coordination using [Dagster](https://dagster.io/).

Manages job schedules, asset dependencies, and concurrency control for the full data pipeline.

## Documentation

Full documentation is in [docs/](./docs/README.md):

- [Jobs](./docs/JOBS.md) — Job definitions and configurations
- [Assets](./docs/ASSETS.md) — Asset dependency graph
- [Schedules](./docs/SCHEDULES.md) — Schedule definitions and conflict resolution
- [Resources](./docs/RESOURCES.md) — Dagster resources

## Quick Start

```bash
# Start Dagster UI (development)
dagster dev

# Validate definitions
dagster definitions validate

# Execute a job manually
dagster job execute -j sapo_nightly_reconciliation_job
```

→ See [System Architecture](../docs/architecture/overview.md) for how orchestration fits into the full pipeline.

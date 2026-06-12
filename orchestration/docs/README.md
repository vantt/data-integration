# Orchestration Layer Documentation

> Job scheduling and coordination using Dagster

## Overview

The orchestration layer manages pipeline scheduling, dependencies, and monitoring using Dagster. It coordinates ingestion, transformation, and serving layers into coherent data pipelines.

## Quick Start

```bash
cd orchestration

# Validate definitions
dagster definitions validate

# Start development UI
dagster dev

# Open http://localhost:3000
```

## Directory Structure

```
orchestration/
├── definitions.py          # Main definitions entry point
├── assets/
│   ├── sapo_assets.py      # Ingestion asset definitions
│   ├── dbt.py              # dbt asset integration
│   └── serving.py          # Serving layer assets
├── jobs/
│   └── __init__.py         # Job definitions
├── schedules/
│   └── __init__.py         # Schedule definitions
├── resources/
│   └── __init__.py         # Resource configurations
└── docs/                   # This documentation
```

## Documentation

| Document | Description |
|----------|-------------|
| [ASSETS.md](./ASSETS.md) | Asset definitions and groups |
| [JOBS.md](./JOBS.md) | Job configurations |
| [SCHEDULES.md](./SCHEDULES.md) | Schedule definitions |
| [RESOURCES.md](./RESOURCES.md) | Resource setup |

## Key Concepts

### Assets

Assets represent data artifacts produced by the pipeline:

```python
@asset(group_name="sapo_ingestion")
def sapo_orders_batch():
    """Batch sync orders from Sapo API"""
    from ingestion.run_orders_batch import main
    return main()
```

### Jobs

Jobs are collections of assets that run together:

```python
pipeline_batch_nightly_job = define_asset_job(
    name="pipeline_batch_nightly_job",
    selection=["sapo_orders_batch", "sapo_customers_batch", "dbt_*", "serving_*"]
)
```

### Schedules

Schedules trigger jobs at specified times:

```python
@schedule(cron_schedule="0 4 * * *", job=pipeline_batch_nightly_job)
def pipeline_batch_nightly_schedule():
    return RunRequest()
```

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DAGSTER ORCHESTRATION                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │ REALTIME JOB    │   │ INCREMENTAL JOB │   │ NIGHTLY JOB     │  │
│  │ Every 1 min     │   │ Every 10 min    │   │ 04:00 AM        │  │
│  │                 │   │                 │   │                 │  │
│  │ • Webhooks      │   │ • History Log   │   │ • Batch sync    │  │
│  │ • dbt (partial) │   │ • dbt (staging) │   │ • dbt (full)    │  │
│  │                 │   │                 │   │ • Serving       │  │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Common Commands

```bash
# Start development server
dagster dev

# Validate definitions
dagster definitions validate

# Run job manually
dagster job execute -j pipeline_batch_nightly_job

# Materialize specific asset
dagster asset materialize -a sapo_orders_batch

# List schedules
dagster schedule list

# Start/stop schedule
dagster schedule start pipeline_batch_nightly_schedule
dagster schedule stop pipeline_batch_nightly_schedule
```

## Configuration

### Environment Variables

```bash
# Required
DATA_LAKE_PATH=/path/to/data_lake
DBT_EXPORT_PATH=/path/to/data_lake/export/marts

# Optional
DAGSTER_HOME=.dagster_home
```

### Dagster Home

```
.dagster_home/
├── dagster.yaml           # Dagster configuration
├── storage/               # Run storage
├── schedules/             # Schedule state
└── logs/                  # Execution logs
```

## Monitoring

### Dagster UI

Access at http://localhost:3000

**Key Pages:**
- **Overview** - System health dashboard
- **Assets** - Asset lineage and freshness
- **Runs** - Execution history
- **Schedules** - Active schedules
- **Jobs** - Job definitions

### Health Checks

```bash
# Check daemon status
dagster-daemon status

# Check for failed runs
dagster run list --status FAILURE
```

## Troubleshooting

### Schedule Not Running

```bash
# Ensure daemon is running
dagster-daemon run &

# Check schedule status
dagster schedule list
```

### Asset Materialization Failed

```bash
# Check run logs
dagster run view <run_id>

# Retry specific asset
dagster asset materialize -a failed_asset
```

### Resource Not Found

Ensure resources are properly configured in `definitions.py`:

```python
defs = Definitions(
    assets=all_assets,
    jobs=all_jobs,
    schedules=all_schedules,
    resources={
        "dbt": DbtCliResource(project_dir=...),
    }
)
```

## Related

- [Main Documentation](../../docs/README.md)
- [Operations Manual](../../docs/operations/operations.md)
- [Architecture](../../docs/architecture/overview.md)

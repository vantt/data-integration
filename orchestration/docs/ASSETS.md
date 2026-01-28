# Asset Documentation

> Dagster asset definitions and groups

## Asset Overview

Assets represent data artifacts in the pipeline. Each asset has:
- **Name**: Unique identifier
- **Group**: Logical grouping
- **Dependencies**: Upstream assets
- **Materialization**: How to produce the asset

## Asset Groups

### sapo_ingestion

Ingestion assets that extract data from Sapo.

| Asset | Description | Schedule |
|-------|-------------|----------|
| `sapo_orders_batch` | Batch sync orders | Nightly |
| `sapo_customers_batch` | Batch sync customers | Nightly |
| `sapo_accounts_batch` | Batch sync accounts | Weekly |
| `sapo_history_log` | History log polling | 10 min |
| `sapo_webhook_consumer` | Webhook processing | 1 min |

### dbt_assets

Transformation assets managed by dbt.

| Asset | Description | Dependencies |
|-------|-------------|--------------|
| `stg_sapo_orders` | Deduplicated orders | sapo_* |
| `stg_sapo_customers` | Deduplicated customers | sapo_* |
| `fact_orders` | Order fact table | stg_* |
| `dim_customers` | Customer dimension | stg_* |

### serving_layer

Serving layer assets for BI.

| Asset | Description | Dependencies |
|-------|-------------|--------------|
| `serving_database` | DuckDB serving views | fact_*, dim_* |

---

## Asset Definitions

### sapo_orders_batch

```python
@asset(
    group_name="sapo_ingestion",
    description="Batch sync orders from Sapo JSON API",
    compute_kind="dlt"
)
def sapo_orders_batch() -> None:
    """
    Incrementally sync orders using modified_on cursor.
    Writes to: data_lake/sapo_raw/order/ingest_method=batch_sync/
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ingestion"))
    from run_orders_batch import main
    main()
```

**Output:**
- Parquet files in `data_lake/sapo_raw/order/ingest_method=batch_sync/`
- dlt state updated with cursor position

---

### sapo_webhook_consumer

```python
@asset(
    group_name="sapo_ingestion",
    description="Process webhooks from D1 buffer",
    compute_kind="dlt"
)
def sapo_webhook_consumer() -> None:
    """
    Poll and process webhook events from Cloudflare D1.
    Writes to: data_lake/sapo_raw/{entity}/ingest_method=webhook/
    """
    from run_webhook_consumer import main
    main(once=True)
```

**Schedule:** Every 1 minute via `sapo_realtime_sync_job`

---

### sapo_history_log

```python
@asset(
    group_name="sapo_ingestion",
    description="Gap-filling via history log API",
    compute_kind="dlt"
)
def sapo_history_log() -> None:
    """
    Poll history log to catch missed events.
    Writes to: data_lake/sapo_raw/{entity}/ingest_method=history_log/
    """
    from run_history_log import main
    main()
```

**Schedule:** Every 10 minutes via `sapo_incremental_sync_job`

---

### dbt_assets

dbt models are loaded as Dagster assets:

```python
from dagster_dbt import DbtCliResource, dbt_assets

@dbt_assets(manifest=dbt_manifest_path)
def all_dbt_assets(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
```

**Asset Mapping:**
- Each dbt model becomes a Dagster asset
- Dependencies auto-discovered from `ref()`
- Tags mapped to Dagster groups

---

### serving_database

```python
@asset(
    group_name="serving_layer",
    description="Generate DuckDB serving database with views",
    deps=["fact_orders", "dim_customers", "dim_products"],
    compute_kind="duckdb"
)
def serving_database() -> None:
    """
    Create smart views pointing to latest Parquet snapshots.
    Output: data_lake/serving/olap.duckdb
    """
    from scripts.provisioning.generate_serving_db import main
    main()
```

**Dependencies:** All mart assets must complete first

---

## Asset Dependencies

```
                    ┌─────────────────────┐
                    │  sapo_orders_batch  │
                    └──────────┬──────────┘
                               │
┌─────────────────────┐        │        ┌─────────────────────┐
│ sapo_webhook_consumer├───────┼────────┤ sapo_history_log    │
└──────────┬──────────┘        │        └──────────┬──────────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   stg_sapo_orders   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     fact_orders     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  serving_database   │
                    └─────────────────────┘
```

---

## Asset Configuration

### Metadata

```python
@asset(
    group_name="sapo_ingestion",
    metadata={
        "source": "Sapo API",
        "owner": "data-eng@company.com",
        "sla": "< 1 hour"
    }
)
def sapo_orders_batch(): ...
```

### Freshness Policies

```python
from dagster import FreshnessPolicy

@asset(
    freshness_policy=FreshnessPolicy(
        maximum_lag_minutes=60,
        cron_schedule="0 * * * *"  # Hourly
    )
)
def sapo_orders_batch(): ...
```

### Partitions

```python
from dagster import DailyPartitionsDefinition

@asset(
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01")
)
def sapo_orders_batch(context) -> None:
    partition_date = context.partition_key
    # Process for specific date
```

---

## Materializing Assets

### Via UI

1. Navigate to Assets
2. Select asset(s)
3. Click "Materialize"

### Via CLI

```bash
# Single asset
dagster asset materialize -a sapo_orders_batch

# Multiple assets
dagster asset materialize -a sapo_orders_batch -a sapo_customers_batch

# All in group
dagster asset materialize --select "group:sapo_ingestion"
```

### Via Code

```python
from dagster import materialize

result = materialize([sapo_orders_batch])
```

---

## Related

- [Jobs](./JOBS.md)
- [Schedules](./SCHEDULES.md)
- [Resources](./RESOURCES.md)

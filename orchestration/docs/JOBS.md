# Job Documentation

> Dagster job definitions and configurations

## Job Overview

Jobs are collections of assets that execute together. Each job has:
- **Name**: Unique identifier
- **Selection**: Which assets to include
- **Config**: Runtime configuration

## Active Jobs

| Job | Schedule | Assets | Purpose |
|-----|----------|--------|---------|
| `sapo_realtime_sync_job` | */1 * * * * | Webhooks + dbt OTP | Real-time updates |
| `sapo_incremental_sync_job` | */10 * * * * | History log + dbt OTP | Gap filling |
| `sapo_nightly_reconciliation_job` | 0 4 * * * | All ingestion + dbt + serving | Full reconciliation |
| `sapo_targets_sync_job` | Manual | Targets only | Google Sheets sync |

---

## Job Definitions

### sapo_realtime_sync_job

**Purpose:** Process webhook events and update operational tables.

```python
sapo_realtime_sync_job = define_asset_job(
    name="sapo_realtime_sync_job",
    selection=[
        "sapo_webhook_consumer",
        *dbt_assets_tagged("otp")
    ],
    description="Process real-time webhook events"
)
```

**Schedule:** Every 1 minute

**Assets Included:**
- `sapo_webhook_consumer`
- `stg_sapo_orders`
- `stg_sapo_customers`

**Execution Flow:**
```
sapo_webhook_consumer
         │
         ▼
    stg_sapo_orders
         │
         ▼
  (OTP models updated)
```

---

### sapo_incremental_sync_job

**Purpose:** Gap filling via history log and incremental dbt updates.

```python
sapo_incremental_sync_job = define_asset_job(
    name="sapo_incremental_sync_job",
    selection=[
        "sapo_history_log",
        *dbt_assets_tagged("otp")
    ],
    description="Incremental sync via history log"
)
```

**Schedule:** Every 10 minutes

**Assets Included:**
- `sapo_history_log`
- `stg_sapo_*`

---

### sapo_nightly_reconciliation_job

**Purpose:** Full daily reconciliation and mart refresh.

```python
sapo_nightly_reconciliation_job = define_asset_job(
    name="sapo_nightly_reconciliation_job",
    selection=[
        "sapo_orders_batch",
        "sapo_customers_batch",
        "sapo_accounts_batch",
        *dbt_assets_tagged("olap"),
        "serving_database"
    ],
    description="Nightly full reconciliation"
)
```

**Schedule:** 04:00 AM daily (Asia/Ho_Chi_Minh)

**Assets Included:**
- All batch ingestion assets
- All dbt models (staging + marts)
- Serving database generation

**Execution Flow:**
```
┌──────────────────┐  ┌───────────────────┐  ┌─────────────────┐
│ sapo_orders_batch│  │sapo_customers_batch│  │sapo_accounts_batch│
└────────┬─────────┘  └─────────┬─────────┘  └────────┬────────┘
         │                      │                     │
         └──────────────────────┼─────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │      dbt_assets       │
                    │  (staging → marts)    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   serving_database    │
                    └───────────────────────┘
```

---

### sapo_targets_sync_job

**Purpose:** Manual sync of sales targets from Google Sheets.

```python
sapo_targets_sync_job = define_asset_job(
    name="sapo_targets_sync_job",
    selection=["sapo_targets"],
    description="Sync sales targets from Google Sheets"
)
```

**Schedule:** Manual trigger only

---

## Job Configuration

### Runtime Config

```python
@job(config={
    "ops": {
        "sapo_orders_batch": {
            "config": {
                "backfill_days": 7
            }
        }
    }
})
def custom_backfill_job(): ...
```

### Tags

```python
sapo_nightly_reconciliation_job = define_asset_job(
    name="sapo_nightly_reconciliation_job",
    selection=[...],
    tags={
        "team": "data-eng",
        "priority": "high",
        "dagster/max_retries": 2
    }
)
```

### Executor

```python
from dagster import multiprocess_executor

sapo_nightly_reconciliation_job = define_asset_job(
    name="sapo_nightly_reconciliation_job",
    selection=[...],
    executor_def=multiprocess_executor.configured({
        "max_concurrent": 4
    })
)
```

---

## Running Jobs

### Via UI

1. Navigate to Jobs
2. Select job
3. Click "Launch Run"
4. Optionally configure parameters
5. Click "Launch"

### Via CLI

```bash
# Run with defaults
dagster job execute -j sapo_nightly_reconciliation_job

# Run with config
dagster job execute -j sapo_nightly_reconciliation_job \
  --config-json '{"ops": {"sapo_orders_batch": {"config": {"backfill_days": 30}}}}'

# Run in background
dagster job launch -j sapo_nightly_reconciliation_job
```

### Via Code

```python
from dagster import execute_job

result = execute_job(
    sapo_nightly_reconciliation_job,
    run_config={...}
)
```

---

## Job Dependencies

Jobs can depend on other jobs completing:

```python
@sensor(job=sapo_nightly_reconciliation_job)
def after_ingestion_sensor(context):
    # Check if ingestion completed
    if ingestion_complete():
        yield RunRequest()
```

---

## Monitoring Jobs

### Run Status

```bash
# List recent runs
dagster run list

# View specific run
dagster run view <run_id>

# Failed runs only
dagster run list --status FAILURE
```

### UI Monitoring

- **Runs page**: See all executions
- **Timeline**: Gantt chart of steps
- **Logs**: Detailed execution logs

---

## Related

- [Assets](./ASSETS.md)
- [Schedules](./SCHEDULES.md)
- [Resources](./RESOURCES.md)

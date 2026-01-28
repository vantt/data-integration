# Configuration Reference

> dlt configuration files and environment variables

## Configuration Files

### secrets.toml

Location: `ingestion/.dlt/secrets.toml`

**This file is gitignored.** Create from template:

```bash
cp .dlt/secrets.toml.example .dlt/secrets.toml
```

```toml
# Sapo API Credentials
[sources.sapo]
api_key = "your_api_key"
api_secret = "your_api_secret"
store_url = "https://yourstore.mysapo.net"

# Cloudflare D1 (Webhook Buffer)
[sources.cloudflare_d1]
api_token = "your_cloudflare_api_token"
account_id = "your_cloudflare_account_id"
database_id = "your_d1_database_id"
worker_url = "https://your-webhook-worker.workers.dev"

# Google Sheets (Targets)
[sources.google_sheets]
credentials_path = "path/to/service-account.json"
spreadsheet_id = "your_spreadsheet_id"

# Filesystem Destination
[destination.filesystem]
bucket_url = "file:///path/to/data_lake/sapo_raw"
```

### config.toml

Location: `ingestion/.dlt/config.toml`

```toml
# Runtime Configuration
[runtime]
log_level = "INFO"  # DEBUG, INFO, WARNING, ERROR
dlthub_telemetry = false

# Extract Configuration
[extract]
max_parallel_items = 5        # Parallel API requests
workers = 4                   # Thread pool size

# Normalize Configuration
[normalize]
loader_file_format = "parquet"

# Load Configuration
[load]
raise_on_failed_jobs = true   # Fail fast on errors

# Source-specific Configuration
[sources.sapo_orders]
page_size = 250               # Items per API page
max_retries = 3               # Retry count on failure
retry_delay = 5               # Seconds between retries

[sources.sapo_customers]
page_size = 250

[sources.webhook_consumer]
batch_size = 1000             # Messages per poll
poll_interval = 60            # Seconds between polls
lock_timeout = 300            # Lock TTL in seconds

[sources.history_log]
poll_interval = 600           # Seconds (10 minutes)
lookback_hours = 24           # How far back to check
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATA_LAKE_PATH` | Base path for data lake | `/path/to/data_lake` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `DLT_LOG_LEVEL` | Logging verbosity | `INFO` |
| `DLT_DATA_DIR` | dlt state directory | `~/.dlt` |
| `TZ` | Timezone | `UTC` |

### Setting Environment Variables

```bash
# Windows (PowerShell)
$env:DATA_LAKE_PATH = "D:/_1.FWG_PARA/.../data_lake"
$env:DLT_LOG_LEVEL = "DEBUG"

# Linux/Mac
export DATA_LAKE_PATH="/path/to/data_lake"
export DLT_LOG_LEVEL="DEBUG"
```

## Destination Configuration

### Filesystem (Local Parquet)

```toml
[destination.filesystem]
bucket_url = "file:///absolute/path/to/data_lake/sapo_raw"
# Or relative (from working directory)
# bucket_url = "file://./data_lake/sapo_raw"
```

### Layout Configuration

Data is automatically partitioned by the pipeline:

```python
# In source code
@dlt.resource(
    write_disposition="append",
    primary_key="entity_id"
)
def orders():
    yield {
        "entity_id": "123",
        "ingest_method": "batch_sync",  # Partition key
        "year": "2026",                  # Partition key
        "month": "01",                   # Partition key
        "payload": {...}
    }
```

Output path structure:
```
{bucket_url}/order/ingest_method={method}/year={year}/month={month}/*.parquet
```

## Credential Management

### Best Practices

1. **Never commit secrets.toml** - It's in .gitignore
2. **Use environment variables** for CI/CD
3. **Rotate credentials regularly**
4. **Limit API key permissions**

### Loading Credentials

dlt automatically loads credentials in this order:

1. Environment variables (highest priority)
2. `secrets.toml`
3. Default values in code

```python
# Code fallback
import dlt

@dlt.source
def my_source(
    api_key: str = dlt.secrets.value  # From secrets.toml or env
):
    pass
```

### Environment Variable Names

dlt converts TOML paths to environment variables:

| TOML Path | Environment Variable |
|-----------|---------------------|
| `[sources.sapo].api_key` | `SOURCES__SAPO__API_KEY` |
| `[destination.filesystem].bucket_url` | `DESTINATION__FILESYSTEM__BUCKET_URL` |

## Logging Configuration

### Log Levels

| Level | Description |
|-------|-------------|
| DEBUG | All details including API responses |
| INFO | Normal operations |
| WARNING | Potential issues |
| ERROR | Failures only |

### Enable Debug Logging

```bash
# Via environment
export DLT_LOG_LEVEL=DEBUG

# Via config.toml
[runtime]
log_level = "DEBUG"
```

### Log Location

Logs are written to:
- Console (stdout/stderr)
- `.dlt/pipeline_traces/` (execution traces)

---

## Related

- [Pipelines](./PIPELINES.md)
- [Sources](./SOURCES.md)
- [Troubleshooting](../../docs/TROUBLESHOOTING.md)

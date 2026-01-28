# Pipeline Documentation

> Detailed documentation for each dlt pipeline

## Table of Contents

1. [Orders Pipeline](#orders-pipeline)
2. [Customers Pipeline](#customers-pipeline)
3. [Accounts Pipeline](#accounts-pipeline)
4. [History Log Pipeline](#history-log-pipeline)
5. [Webhook Consumer](#webhook-consumer)
6. [Targets Pipeline](#targets-pipeline)

---

## Orders Pipeline

**Script:** `run_orders_batch.py`
**Pipeline Name:** `sapo_orders`
**Schedule:** Daily at 04:00 AM

### Purpose

Incrementally sync orders from Sapo JSON API using `modified_on` cursor.

### Usage

```bash
# Standard incremental run
python run_orders_batch.py

# Backfill historical data
python run_orders_batch.py --backfill --days 90

# Dry run (no writes)
python run_orders_batch.py --dry-run
```

### Configuration

```toml
# .dlt/config.toml
[sources.sapo_orders]
page_size = 250
max_retries = 3
```

### Data Flow

```
Sapo API (/admin/orders.json)
    │
    │ GET with modified_on_min cursor
    ▼
dlt Source (sapo_orders)
    │
    │ Paginate, transform to envelope
    ▼
dlt Pipeline
    │
    │ Normalize, write Parquet
    ▼
data_lake/sapo_raw/order/ingest_method=batch_sync/
```

### Incremental Logic

```python
@dlt.source
def sapo_orders(
    modified_on: dlt.sources.incremental[str] = dlt.sources.incremental(
        cursor_path="modified_on",
        initial_value="2024-01-01T00:00:00Z"
    )
):
    # Fetch orders where modified_on >= cursor
    # Update cursor to MAX(modified_on) after load
```

### Output Schema

| Column | Type | Description |
|--------|------|-------------|
| entity_id | VARCHAR | Order ID |
| entity_type | VARCHAR | "order" |
| ingest_method | VARCHAR | "batch_sync" |
| event_type | VARCHAR | "snapshot" |
| event_timestamp | TIMESTAMP | modified_on value |
| payload | JSON | Full order object |

---

## Customers Pipeline

**Script:** `run_customers_batch.py`
**Pipeline Name:** `sapo_customers`
**Schedule:** Daily at 04:30 AM

### Purpose

Incrementally sync customers using `created_on` cursor.

> **Note:** Customer updates cannot be reliably tracked via batch API. Use webhooks and history log for update events.

### Usage

```bash
python run_customers_batch.py
python run_customers_batch.py --backfill --days 90
```

### Limitations

- Only captures new customers (created_on)
- Updates require webhook/history log channels
- Full refresh recommended weekly for data quality

---

## Accounts Pipeline

**Script:** `run_accounts_batch.py`
**Pipeline Name:** `sapo_accounts`
**Schedule:** Weekly

### Purpose

Full sync of staff accounts. Small dataset, no incremental needed.

### Usage

```bash
python run_accounts_batch.py
```

### Data Volume

- Typically < 100 records
- Full refresh takes < 1 minute

---

## History Log Pipeline

**Script:** `run_history_log.py`
**Pipeline Name:** `sapo_history_log`
**Schedule:** Every 10 minutes

### Purpose

Poll Sapo history log API to capture events missed by webhooks.

### Usage

```bash
# Standard run
python run_history_log.py

# Backfill specific date range
python run_history_log.py --from "2026-01-01" --to "2026-01-15"
```

### Data Flow

```
Sapo API (/admin/settings/get_logs)
    │
    │ GET with occur_at cursor
    ▼
Parse log entries
    │
    │ Extract entity_type, entity_id, action
    ▼
Fetch full entity (/admin/{entity}/{id}.json)
    │
    ▼
Wrap in envelope, write Parquet
```

### Log Entry Structure

```json
{
  "id": 12345,
  "subject_type": "Order",
  "subject_id": 67890,
  "action": "update",
  "occur_at": "2026-01-28T10:30:00Z",
  "changes": {...}
}
```

### Supported Entities

| Entity Type | API Endpoint |
|-------------|--------------|
| Order | /admin/orders/{id}.json |
| Customer | /admin/customers/{id}.json |
| Product | /admin/products/{id}.json |

---

## Webhook Consumer

**Script:** `run_webhook_consumer.py`
**Pipeline Name:** `sapo_webhooks`
**Schedule:** Every 1 minute (via Dagster)

### Purpose

Poll Cloudflare D1 buffer and process webhook events.

### Usage

```bash
# Single batch
python run_webhook_consumer.py --once

# Continuous polling
python run_webhook_consumer.py --loop --interval 60

# Custom batch size
python run_webhook_consumer.py --batch-size 500
```

### Data Flow

```
Cloudflare D1 (webhook buffer)
    │
    │ GET /poll?limit=1000
    ▼
dlt Webhook Consumer
    │
    │ Transform to envelope
    ▼
Write Parquet
    │
    ▼
POST /ack-batch (mark processed)
```

### ACK Protocol

1. Fetch batch with lock (5 min TTL)
2. Process and write to Parquet
3. ACK successful IDs
4. Failed messages auto-retry after lock expires

### Error Handling

```python
try:
    messages = client.poll(limit=1000)
    for msg in messages:
        process(msg)
    client.ack_batch([m.id for m in messages])
except Exception as e:
    # Messages will auto-release after lock expires
    log.error(f"Processing failed: {e}")
```

---

## Targets Pipeline

**Script:** `run_targets.py` (via `src/gsheet_targets.py`)
**Pipeline Name:** `sapo_targets`
**Schedule:** Manual

### Purpose

Import sales targets from Google Sheets.

### Usage

```bash
python -c "from src.gsheet_targets import run_targets; run_targets()"
```

### Configuration

```toml
# .dlt/secrets.toml
[sources.google_sheets]
credentials_path = "path/to/service-account.json"
spreadsheet_id = "your-spreadsheet-id"
```

### Sheet Format

| staff_id | staff_name | location_id | period | target_amount |
|----------|------------|-------------|--------|---------------|
| 1001 | Nguyen Van A | 12345 | 2026-01 | 100000000 |

---

## Pipeline State Management

### View State

```python
import dlt

pipeline = dlt.pipeline(pipeline_name='sapo_orders')

# Current state
print(pipeline.state)

# Last trace
print(pipeline.last_trace)

# Incremental cursors
print(pipeline.state.get('sources', {}).get('sapo_orders', {}))
```

### Reset State

```bash
# Remove specific pipeline state
rm -rf .dlt/pipelines/sapo_orders/

# Or reset via code
pipeline.drop()
```

### Backup State

```bash
# State is stored in .dlt/pipelines/
cp -r .dlt/pipelines/ backup/dlt_state/
```

---

## Related

- [Configuration Reference](./CONFIGURATION.md)
- [Sapo API Sources](./SOURCES.md)
- [Incremental Strategies](./INCREMENTAL.md)

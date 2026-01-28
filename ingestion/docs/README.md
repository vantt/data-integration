# Ingestion Layer Documentation

> Data extraction pipelines using dlt (Data Load Tool)

## Overview

The ingestion layer extracts data from Sapo e-commerce platform and loads it into Parquet files. It supports three ingestion channels:

1. **Batch API** - Scheduled full/incremental syncs
2. **Webhooks** - Real-time event processing
3. **History Log** - Gap filling for missed events

## Quick Start

```bash
# Activate virtual environment
cd ingestion
.\venv\Scripts\activate  # Windows

# Run batch sync
python run_orders_batch.py

# Run webhook consumer
python run_webhook_consumer.py --loop

# Run history log
python run_history_log.py
```

## Directory Structure

```
ingestion/
├── run_orders_batch.py      # Order batch sync entry point
├── run_customers_batch.py   # Customer batch sync
├── run_accounts_batch.py    # Account full sync
├── run_history_log.py       # History log polling
├── run_webhook_consumer.py  # Webhook processing
├── src/
│   ├── sapo_client.py       # Sapo API client
│   ├── sapo_orders.py       # Orders source
│   ├── sapo_customers.py    # Customers source
│   ├── sapo_accounts.py     # Accounts source
│   ├── history_log.py       # History log source
│   ├── webhook_consumer.py  # Webhook consumer
│   └── gsheet_targets.py    # Google Sheets targets
├── .dlt/
│   ├── secrets.toml         # API credentials (gitignored)
│   └── config.toml          # Pipeline configuration
├── requirements.txt         # Python dependencies
└── docs/                    # This documentation
```

## Documentation

| Document | Description |
|----------|-------------|
| [PIPELINES.md](./PIPELINES.md) | Detailed pipeline documentation |
| [CONFIGURATION.md](./CONFIGURATION.md) | Configuration reference |
| [SOURCES.md](./SOURCES.md) | Sapo API specifics |
| [INCREMENTAL.md](./INCREMENTAL.md) | Incremental loading strategies |

## Key Concepts

### Data Envelope

All data is wrapped in a standard envelope format:

```json
{
  "entity_id": "12345",
  "entity_type": "order",
  "ingest_method": "webhook",
  "event_type": "update",
  "event_timestamp": "2026-01-28T10:30:00Z",
  "payload": { "...full entity data..." },
  "_dlt_load_id": "abc123",
  "_dlt_id": "unique-record-id"
}
```

### Partition Strategy

Data is partitioned by:
1. `ingest_method` (batch_sync, webhook, history_log)
2. `year` (YYYY)
3. `month` (MM)

Output path: `data_lake/sapo_raw/{entity}/ingest_method={X}/year={Y}/month={M}/`

### Incremental Cursors

| Pipeline | Cursor Field | Strategy |
|----------|--------------|----------|
| Orders | `modified_on` | Incremental by modification time |
| Customers | `created_on` | Incremental by creation time |
| Accounts | N/A | Full refresh |
| History Log | `occur_at` | Incremental by event time |
| Webhooks | Message ID | ACK-based (at-least-once) |

## Common Commands

```bash
# Batch sync with backfill
python run_orders_batch.py --backfill --days 30

# Webhook consumer (single run)
python run_webhook_consumer.py --once

# Webhook consumer (continuous)
python run_webhook_consumer.py --loop --interval 60

# History log
python run_history_log.py

# Dry run (no data written)
python run_orders_batch.py --dry-run
```

## Troubleshooting

### Check Pipeline State

```python
import dlt
pipeline = dlt.pipeline(pipeline_name='sapo_orders')
print(pipeline.state)
print(pipeline.last_trace)
```

### Reset Pipeline

```bash
# Remove state to re-sync from beginning
rm -rf .dlt/pipelines/sapo_orders/
```

### Debug Mode

```bash
export DLT_LOG_LEVEL=DEBUG
python run_orders_batch.py
```

## Related

- [Main Documentation](../../docs/README.md)
- [Data Flow](../../docs/DATA_FLOW.md)
- [Architecture](../../docs/ARCHITECTURE.md)

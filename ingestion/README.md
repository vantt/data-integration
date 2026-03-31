# Ingestion Layer

Data extraction pipelines using [dlt](https://dlthub.com/) (Data Load Tool).

Extracts data from Sapo e-commerce platform via three channels (Batch API, Webhooks, History Log) and loads into partitioned Parquet files.

## Documentation

Full documentation is in [docs/](./docs/README.md):

- [Sources](./docs/SOURCES.md) — Sapo API endpoint reference
- [Pipelines](./docs/PIPELINES.md) — Pipeline definitions and scripts
- [Incremental](./docs/INCREMENTAL.md) — Incremental loading strategy
- [Configuration](./docs/CONFIGURATION.md) — dlt config and secrets
- [Deployment](./docs/DEPLOYMENT.md) — Ingestion-specific deployment

## Quick Start

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Sync orders (incremental)
python run_orders_batch.py

# Sync customers
python run_customers_batch.py

# Process webhooks
python run_webhook_consumer.py --once
```

→ See [System Architecture](../docs/architecture/overview.md) for how ingestion fits into the full pipeline.

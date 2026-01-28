# Data Integration Pipeline

> Modern data lakehouse for Sapo e-commerce using dlt, dbt, Dagster & DuckDB

## Overview

A production-grade ETL pipeline that syncs data from Sapo retail platform to a local data lakehouse. The system supports three ingestion channels (Batch API, Webhooks, History Log) and transforms data through a 7-hop pipeline to serve analytics via Metabase.

**Key Features:**
- Multi-channel data ingestion with automatic deduplication
- Immutable data lake using Parquet files
- Zero-downtime serving with rolling snapshots
- Dimensional modeling (Kimball star schema)
- Cost-effective: runs entirely on local infrastructure

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├──────────────────┬──────────────────┬───────────────────────────────────────┤
│   Batch API      │    Webhooks      │           History Log                 │
│  (Daily/Hourly)  │   (Real-time)    │         (Gap Filling)                 │
└────────┬─────────┴────────┬─────────┴──────────────┬────────────────────────┘
         │                  │                        │
         ▼                  ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER (dlt)                                │
│              Python scripts extracting data to Parquet files                 │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAW STORAGE (Parquet)                                │
│     data_lake/sapo_raw/{entity}/ingest_method={X}/year={Y}/month={M}/       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION LAYER (dbt + DuckDB)                     │
│         Staging → Intermediate → Marts (Star Schema)                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVING LAYER                                        │
│              DuckDB Views + Metabase Dashboards                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- Git
- Docker (for Metabase)
- Sapo API credentials

### Installation

```bash
# 1. Clone repository
git clone <repo-url>
cd data-integration2

# 2. Create virtual environment
cd ingestion
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .dlt/secrets.toml.example .dlt/secrets.toml
# Edit secrets.toml with your Sapo API credentials

# 5. Run first ingestion
python run_orders_batch.py
```

### Verify Installation

```bash
# Check data was loaded
python ../scripts/testing/verify_hops_readonly.py

# Run dbt transformation
python ../transformation/scripts/run_dbt.py --select +tag:mart

# Start Dagster UI (optional)
cd ../orchestration
dagster dev
```

## Project Structure

```
data-integration2/
├── ingestion/              # Data extraction (dlt pipelines)
│   ├── run_*.py            # Pipeline entry points
│   ├── src/                # Source modules
│   └── .dlt/               # dlt configuration
│
├── transformation/         # Data transformation (dbt)
│   ├── models/             # SQL models
│   │   ├── staging/        # Deduplication & cleaning
│   │   ├── intermediate/   # Business logic
│   │   └── marts/          # Dimensional tables
│   ├── macros/             # dbt utilities
│   └── scripts/            # dbt wrapper scripts
│
├── orchestration/          # Job scheduling (Dagster)
│   ├── definitions.py      # Asset & job definitions
│   ├── assets/             # Asset modules
│   └── schedules/          # Schedule configurations
│
├── webhook_receiver/       # Webhook buffering (Cloudflare D1)
│   └── cloudflareD1/       # Worker implementation
│
├── webhook_consumer/       # Webhook polling
│   └── cloudflared1_consumer/
│
├── data_lake/              # Data storage
│   ├── sapo_raw/           # Raw Parquet files
│   ├── export/marts/       # Transformed data
│   └── serving/            # DuckDB serving database
│
├── scripts/                # Utilities
│   ├── provisioning/       # DB setup scripts
│   ├── testing/            # Verification scripts
│   └── maintenance/        # Cleanup scripts
│
├── docs/                   # Documentation
├── AGENTS.md               # AI agent context
└── README.md               # This file
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Ingestion | [dlt](https://dlthub.com/) | Data extraction & loading |
| Storage | Parquet + DuckDB | Immutable data lake |
| Transformation | [dbt](https://www.getdbt.com/) | SQL-based ELT |
| Orchestration | [Dagster](https://dagster.io/) | Job scheduling |
| Serving | DuckDB + Metabase | Analytics & BI |
| Webhooks | Cloudflare Workers | Real-time event buffering |

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design & principles |
| [Data Flow](docs/DATA_FLOW.md) | End-to-end pipeline flow |
| [Data Dictionary](docs/DATA_DICTIONARY.md) | Schema & entity reference |
| [Deployment](docs/DEPLOYMENT.md) | Setup & configuration guide |
| [Operations](docs/OPERATIONS.md) | Daily operations & monitoring |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Problem solving guide |

### Component Documentation

- [Ingestion Layer](ingestion/docs/README.md) - dlt pipeline details
- [Transformation Layer](transformation/docs/README.md) - dbt model documentation
- [Orchestration Layer](orchestration/docs/README.md) - Dagster jobs & schedules
- [Webhook Receiver](webhook_receiver/docs/README.md) - Cloudflare Worker setup

## Common Commands

```bash
# Ingestion
python ingestion/run_orders_batch.py          # Sync orders
python ingestion/run_customers_batch.py       # Sync customers
python ingestion/run_history_log.py           # Gap filling
python ingestion/run_webhook_consumer.py      # Process webhooks

# Transformation
python transformation/scripts/run_dbt.py --select +tag:mart
python transformation/scripts/run_dbt.py --select +tag:otp   # OTP layer only

# Orchestration
dagster dev                                   # Start Dagster UI
dagster job execute -j sapo_nightly_reconciliation_job

# Serving
python scripts/provisioning/generate_serving_db.py
```

## Development

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development workflow, code standards, and PR process.

### Running Tests

```bash
# Verify data integrity
python scripts/testing/verify_hops_readonly.py

# Test OLAP queries
python scripts/testing/test_olap_queries.py

# dbt tests
python transformation/scripts/run_dbt.py test
```

## License

Proprietary - Internal use only.

---

**Maintained by:** Data Engineering Team
**Last Updated:** 2026-01-28

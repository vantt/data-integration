# Deployment Guide

> Complete setup and configuration guide for the Data Integration Pipeline

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Component Deployment](#component-deployment)
4. [Initial Data Load](#initial-data-load)
5. [Verification](#verification)
6. [Production Checklist](#production-checklist)

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 / Linux | Windows 11 / Ubuntu 22.04 |
| CPU | 2 cores | 4+ cores |
| RAM | 8 GB | 16 GB |
| Disk | 20 GB free | 50+ GB SSD |
| Python | 3.10+ | 3.11+ |
| Docker | 20.10+ | Latest |

### External Services

| Service | Purpose | Required |
|---------|---------|----------|
| Sapo Account | API access | Yes |
| Cloudflare Account | Webhook buffering | For webhooks |
| Google Sheets | Targets data | Optional |

### Required Credentials

Before starting, gather these credentials:

1. **Sapo API**
   - Store URL (e.g., `https://yourstore.mysapo.net`)
   - API Key
   - API Secret

2. **Cloudflare** (for webhooks)
   - Account ID
   - D1 Database ID
   - API Token

---

## Environment Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd data-integration2
```

### Step 2: Python Virtual Environment

```bash
# Navigate to ingestion folder
cd ingestion

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configuration Files

#### 3.1 dlt Secrets (`ingestion/.dlt/secrets.toml`)

```bash
# Copy template
cp .dlt/secrets.toml.example .dlt/secrets.toml
```

Edit `secrets.toml`:

```toml
[sources.sapo]
api_key = "your_api_key"
api_secret = "your_api_secret"
store_url = "https://yourstore.mysapo.net"

[sources.cloudflare_d1]
api_token = "your_cloudflare_api_token"
account_id = "your_account_id"
database_id = "your_d1_database_id"
worker_url = "https://your-worker.workers.dev"

[destination.filesystem]
bucket_url = "file://D:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/sapo_raw"
```

#### 3.2 dlt Config (`ingestion/.dlt/config.toml`)

```toml
[runtime]
log_level = "INFO"

[extract]
max_parallel_items = 5

[normalize]
loader_file_format = "parquet"

[load]
raise_on_failed_jobs = true
```

#### 3.3 Environment Variables (`.env`)

Create `.env` at repository root for LOCAL DEVELOPMENT:

```bash
# Data paths (local filesystem, not Docker)
DATA_LAKE_PATH=D:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake
DBT_EXPORT_PATH=D:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/export/marts

# Metabase
METABASE_URL=http://127.0.0.1:3000
METABASE_API_KEY=your_metabase_api_key

# Timezone
TZ=Asia/Ho_Chi_Minh
```

For DOCKER DEPLOYMENT, create `.env.docker`:

```bash
# Docker paths (use /app/var/ for data, /app/ for code)
DBT_DATA_LAKE_PATH=/app/var/data_lake
DBT_EXPORT_PATH=/app/var/data_lake/export/marts
DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/var/data_lake
BACKUP_ROOT=/app/var/backups
DAGSTER_HOME=/app/var/dagster_home
SHOPEE_INPUT_DIR=/app/var/input_source/shopee

# Metabase
METABASE_URL=http://127.0.0.1:3000
METABASE_API_KEY=your_metabase_api_key

# Timezone
TZ=Asia/Ho_Chi_Minh
```

#### 3.4 dbt Profile (`transformation/profiles.yml`)

```yaml
sapo_analytics:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DATA_LAKE_PATH') }}/sapo_warehouse.duckdb"
      schema: main
      threads: 4
      extensions:
        - parquet
        - json
```

---

## Component Deployment

### Deploy Ingestion Layer

```bash
cd ingestion

# Verify configuration
python -c "import dlt; print(dlt.__version__)"

# Test Sapo connection
python -c "
from src.sapo_client import SapoClient
client = SapoClient()
print('Connection OK' if client.test_connection() else 'Failed')
"
```

### Deploy Transformation Layer

```bash
cd transformation

# Install dbt packages
python scripts/run_dbt.py deps

# Verify dbt connection
python scripts/run_dbt.py debug

# Expected output:
# All checks passed!
```

### Deploy Orchestration Layer

```bash
cd orchestration

# Validate Dagster definitions
dagster definitions validate

# Expected output:
# Definitions validated.

# Start Dagster UI (development)
dagster dev
# Open http://localhost:3000
```

### Deploy Webhook Receiver (Cloudflare)

```bash
cd webhook_receiver/cloudflareD1

# Install dependencies
npm install

# Deploy to Cloudflare
npx wrangler publish

# Verify deployment
curl https://your-worker.workers.dev/health
# Expected: {"status":"ok"}
```

### Deploy Metabase (Docker)

**Volume Structure:**

Docker containers mount data directories at `/app/var/` and code at `/app/`:

```bash
# docker-compose.yml volume mounts:
volumes:
  # Code (stateless, git-tracked)
  - ./transformation:/app/transformation
  - ./ingestion:/app/ingestion
  - ./orchestration:/app/orchestration
  - ./scripts:/app/scripts
  # Data (stateful, persistent) — grouped under /app/var/
  - ./app_data/data_lake:/app/var/data_lake
  - ./app_data/dagster_home:/app/var/dagster_home
  - ./app_data/logs:/app/var/logs
  - ./app_data/backups:/app/var/backups
  - ./app_data/input_source:/app/var/input_source
```

**Run Metabase:**

```bash
# From repository root (using docker-compose)
docker compose up -d metabase

# OR: standalone container
docker run -d \
  --name metabase \
  -p 3000:3000 \
  -v ./app_data/data_lake:/app/var/data_lake \
  metabase-duckdb

# Check logs
docker logs -f metabase
```

**Metabase Configuration:**

1. Open http://localhost:3000
2. Complete initial setup wizard
3. Add Database:
   - Type: DuckDB
   - Path: `/app/var/data_lake/serving/olap.duckdb`
4. Name: "Sapo"

**Critical: Serving Views After Mount Changes**

If you change Docker volume mount paths, you MUST regenerate serving views:

```bash
# Stop Metabase first (releases DuckDB lock)
docker compose down

# Then regenerate
docker compose up -d data_platform
docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py

# Restart Metabase
docker compose up -d metabase
```

Reason: Serving view SQL contains absolute paths to Parquet files. Path changes require view regeneration.

**Also clean dbt target cache** — cached state references old absolute paths for rolling parquet output:

```bash
docker exec data_platform bash -c "rm -rf /app/transformation/target"
# Then trigger a full dbt build (or let Dagster startup command handle it via dbt parse)
```

Without this, dbt may fail with `Cannot open file "/app/old_path/rolling/...": No such file or directory`.

---

## Initial Data Load

### Step 1: Run Historical Backfill

```bash
cd ingestion

# Backfill orders (last 30 days)
python run_orders_batch.py --backfill --days 30

# Backfill customers
python run_customers_batch.py --backfill --days 30

# Sync accounts (full)
python run_accounts_batch.py
```

### Step 2: Run Initial Transformation

```bash
cd transformation

# Build all models
python scripts/run_dbt.py run --full-refresh

# Run tests
python scripts/run_dbt.py test
```

### Step 3: Generate Serving Layer

```bash
cd scripts/provisioning

# Generate serving database
python generate_serving_db.py
```

### Step 4: Verify Data Flow

```bash
# Check data at each hop
python scripts/testing/verify_hops_readonly.py
```

Expected output:

```
=== HOP 3: Raw Storage ===
Orders: 1,234 records
Customers: 567 records
Accounts: 23 records

=== HOP 5-6: Staging & Marts ===
stg_sapo_orders: 1,000 rows
stg_sapo_customers: 500 rows
fact_orders: 1,000 rows
dim_customers: 500 rows

=== HOP 7: Serving ===
Views available: 8
Latest snapshot: 2026-01-28 04:00:00
```

---

## Verification

### Verify Ingestion

```bash
cd ingestion

# Check dlt state
python -c "
import dlt
from dlt.common.storages.load_info import LoadInfo
pipeline = dlt.pipeline(pipeline_name='sapo_orders')
print(pipeline.last_trace)
"
```

### Verify Transformation

```bash
cd transformation

# List models
python scripts/run_dbt.py ls --select tag:mart

# Run tests
python scripts/run_dbt.py test

# Generate docs
python scripts/run_dbt.py docs generate
python scripts/run_dbt.py docs serve
```

### Verify Orchestration

```bash
# Start Dagster
dagster dev

# In UI:
# 1. Navigate to Assets
# 2. Click "Materialize all"
# 3. Check job runs completed successfully
```

### Verify Serving

```bash
# Query serving database
python -c "
import duckdb
conn = duckdb.connect('data_lake/serving/olap.duckdb', read_only=True)
print(conn.execute('SHOW TABLES').fetchall())
conn.close()
"
```

### End-to-End Test

```bash
# Run full pipeline
python scripts/testing/test_olap_queries.py

# Expected: All queries complete without errors
```

---

## Production Checklist

### Security

- [ ] API credentials stored in `secrets.toml` (gitignored)
- [ ] `.env` file excluded from git
- [ ] Metabase admin password changed from default
- [ ] Cloudflare Worker HMAC validation enabled
- [ ] Data lake folder permissions restricted

### Reliability

- [ ] Historical backfill completed
- [ ] All dbt tests passing
- [ ] Dagster schedules configured
- [ ] Monitoring alerts configured
- [ ] Backup procedure documented

### Performance

- [ ] DuckDB memory settings optimized
- [ ] Parquet file sizes reasonable (<100MB each)
- [ ] Metabase queries under 3 seconds
- [ ] Batch jobs complete within SLA

### Operations

- [ ] Runbook documented ([OPERATIONS.md](./operations.md))
- [ ] On-call contacts defined
- [ ] Troubleshooting guide available ([TROUBLESHOOTING.md](./troubleshooting.md))
- [ ] Recovery procedures tested

### Monitoring

- [ ] Dagster UI accessible
- [ ] Data freshness alerts configured
- [ ] Error notification channel setup
- [ ] Dashboard health checks enabled

---

## Quick Start Summary

```bash
# 1. Setup environment
cd ingestion && python -m venv venv && .\venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure credentials
cp .dlt/secrets.toml.example .dlt/secrets.toml
# Edit secrets.toml with your credentials

# 3. Run initial load
python run_orders_batch.py --backfill --days 30

# 4. Transform data
cd ../transformation
python scripts/run_dbt.py run --full-refresh

# 5. Generate serving layer
cd ../scripts/provisioning
python generate_serving_db.py

# 6. Start orchestrator
cd ../orchestration
dagster dev

# 7. Access dashboards
# Dagster: http://localhost:3000
# Metabase: http://localhost:3000 (after Docker setup)
```

---

## Docker Deployment (Windows Production)

> This section covers deploying the full platform (Dagster, Consumer, Metabase) via Docker on a Windows machine. For development setup, see sections above.

### Prerequisites

1.  **Windows 10/11 Pro/Enterprise** (Recommended for Hyper-V/WSL2 support).
2.  **Docker Desktop for Windows**: [Download & Install](https://www.docker.com/products/docker-desktop).
    - Enable WSL 2 backend during installation for better performance.

### Installation Steps

#### 1. Copy Project Files

Copy the entire project folder to the target Windows machine.
**Migrating Data?** If you have existing Metabase data, read `./migration.md` first.

Ensure you have the following key files:

- `docker-compose.yml`
- `Dockerfile.metabase` (Metabase)
- `Dockerfile.dataplatform`
- `Dockerfile.rill`
- `.env.example`
- `ingestion/`, `transformation/`, `orchestration/`, `scripts/` folders.

**Directory Structure (Created Automatically):**

```
project-root/
├── app_data/                    # Created automatically on first docker compose up
│   ├── data_lake/               # Maps to /app/var/data_lake in container
│   ├── dagster_home/            # Maps to /app/var/dagster_home in container
│   ├── logs/                    # Maps to /app/var/logs in container
│   ├── backups/                 # Maps to /app/var/backups in container
│   ├── input_source/            # Maps to /app/var/input_source in container
│   ├── metabase_data/           # Metabase H2 database
│   └── rill/                    # Rill configuration
├── docker-compose.yml           # Volume mount configuration
└── [code directories]           # Map to /app/* in container (code)
```

#### 2. Configure Environment Variables

1.  Duplicate `.env.example` and rename it to `.env.prod`.
2.  Open `.env.prod` and fill in your real credentials:
    - **Sapo API**: Keys, secrets, store URL.
    - **Cloudflare/Worker**: URL for the webhook receiver (if applicable).
    - **Metabase DB**: Connection details for the Metabase application database (Postgres).
      - If using a local Postgres on Windows, use `MB_DB_HOST=host.docker.internal`.

#### 3. Build and Run Containers

Open **PowerShell** or **Command Prompt** in the project directory.

##### Option A: Standard (Keep .env.prod)

Run this if you manage the server securely and want easy updates:

```powershell
docker compose up -d --build --remove-orphans
```

##### Option B: High Security (Delete .env.prod)

Run this to inject variables once and immediately delete the file from disk:

```powershell
.\scripts\secure_deploy.ps1
```

- This script opens Notepad for you to paste secrets.
- Runs Docker.
- Deletes `.env.prod` automatically upon success.
- **Note**: If you run `docker compose down`, you will need to re-enter secrets to start again.

#### 4. Verify Services

##### Via Command Line

Check status:

```powershell
docker compose ps
```

You should see 3 services running: `data_platform`, `webhook_consumer`, `metabase`.

##### Via Docker Desktop UI

1.  Open **Docker Desktop**.
2.  Go to the **Containers** tab.
3.  You will see a group named `data-integration2` (or your folder name).
4.  Expand it to see the 3 services (`data_platform`, `webhook_consumer`, `metabase`).
5.  Click on any container to view its **Logs**, **Inspect** variables, or **Stop/Restart** it easily with buttons.

##### Access Applications

- **Dagster UI**: [http://localhost:3001](http://localhost:3001)
- **Metabase**: [http://localhost:3000](http://localhost:3000)

### Docker Maintenance

#### Updating Code

If you modify code in `ingestion`, `transformation`, etc., you need to rebuild:

```powershell
docker compose up -d data_platform --build --remove-orphans
```

#### Cleanup Old Dagster Runs

```
docker compose exec data_platform python scripts/maintenance/purge_dagster_runs.py --keep-days <số ngày> --force
```

#### Viewing Logs

```powershell
docker compose logs -f
```

#### Stopping Services

```powershell
docker compose down
```

To stop and remove volumes (WARNING: Deletes Metabase data if not using external DB):

```powershell
docker compose down -v
```

---

## Next Steps

- [Operations Manual](./operations.md) - Daily operations guide
- [Troubleshooting](./troubleshooting.md) - Common issues and fixes
- [Architecture](../architecture/overview.md) - Understand system design

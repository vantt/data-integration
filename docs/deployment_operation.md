# Deployment & Operations Guide

This document provides guidelines for deploying and operating the Data Warehouse components, including DLT pipelines and the Metabase Serving layer.

---

## 1. DLT Operations

### Configuration

DLT uses a hierarchical configuration system.

- **Secrets (`dlt/.dlt/secrets.toml`)**: Contains sensitive information like database credentials, API keys, and specific destination paths.
  - _Example_: `bucket_url` for filesystem destination, Sapo credentials.
- **Config (`dlt/.dlt/config.toml`)**: Contains non-sensitive, shared configurations.
- **`bucket_url`**: Defines where the Parquet files are stored (Data Lake path).
  - Location: `[destination.filesystem]` in `secrets.toml`.
  - Value: `file:///d:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake`

### State Management

DLT maintains "State" to track what data has been loaded (Incremental Loading).

1.  **Local State (The "Brain")**
    - **Location**: `C:\Users\<User>\.dlt\pipelines\<pipeline_name>`
    - **Effect**: DLT checks this _first_ to determine what data to fetch next.

2.  **Destination State (The Backup)**
    - **Location**: `data_lake/sapo_raw/_dlt_pipeline_state` (or inside the dataset).
    - **Effect**: If Local State is missing, DLT restores state from here to continue loading.

### Troubleshooting

#### Force a Full Refresh (Reset Pipeline)

1.  **Delete Local State**: `rd /s /q C:\Users\<User>\.dlt\pipelines\<pipeline_name>`
2.  **Delete Destination Data**: Remove corresponding folder in `data_lake/sapo_raw/<entity_name>`
3.  **Run Pipeline**: Execute the run script.

#### Common CLI Commands

Run from `dlt/` with `venv` activated.

- `dlt pipeline <pipeline_name> info`: Check status.
- `dlt pipeline <pipeline_name> sync`: Sync state.

---

## 2. Metabase Deployment (Docker)

To serve the OLAP data (Parquet + DuckDB Views), we use Metabase running in a Docker container.

### Prerequisites

- **Docker Desktop** installed on Windows.
- **Git Bash** or PowerShell.

### Directory Structure & Volumes

Critical: We map the local `data_lake` folder to `/data_lake` inside the container.

- **Host Path**: `.\data_lake`
- **Container Path**: `/data_lake`

### Docker Compose Configuration

Create a `docker-compose.yml` file in the project root:

```yaml
version: "3.9"
services:
  metabase:
    image: metabase/metabase:latest
    container_name: metabase_sapo
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      # 1. Mount Data Lake (Read-only recommended for safety, but Read-Write needed if DuckDB writes temp files)
      - ./data_lake:/data_lake

      # 2. Persist Metabase App Data (Users, Dashboards settings)
      - metabase_data:/metabase-data
    environment:
      - MB_DB_FILE=/metabase-data/metabase.db
      - MB_JETTY_PORT=3000

volumes:
  metabase_data:
```

### Setup Steps

1.  **Start Metabase**:

    ```powershell
    docker-compose up -d
    ```

2.  **Access UI**:
    Open [http://localhost:3000](http://localhost:3000)

3.  **Add Data Source**:
    - **Database Type**: DuckDB (You may need to install the DuckDB driver plugin for Metabase if not included, or use the official Metabase image if it supports it. _Note: Standard Metabase might not have DuckDB driver by default. If so, use a custom image or mount the driver jar._)
    - **Display Name**: `Sapo OLAP`
    - **Database File Path**: `/data_lake/serving/olap.duckdb`

    > **Important**: The path MUST be `/data_lake/...` (Docker path), NOT `D:\...`.

---

## 3. Serving Layer Operations

### Updating the Serving View (`olap.duckdb`)

After `dlt` and `dbt` have run, the `olap.duckdb` file needs to have its Views created/updated to point to the new Parquet files.

**Script**: `scripts/update_serving_views.py` (Example)

```python
import duckdb

# Connect to the serving DB file
con = duckdb.connect('data_lake/serving/olap.duckdb')

# Create View pointing to Docker path
con.sql("CREATE OR REPLACE VIEW dim_customers AS SELECT * FROM '/data_lake/export/marts/dim_customers/*.parquet'")
con.sql("CREATE OR REPLACE VIEW fact_orders AS SELECT * FROM '/data_lake/export/marts/fact_orders/*.parquet'")

con.close()
```

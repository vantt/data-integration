# Deployment Guide for Windows

This guide explains how to deploy the Data Integration Platform (Dagster, Consumer, Metabase) on a Windows machine using Docker.

## Prerequisites

1.  **Windows 10/11 Pro/Enterprise** (Recommended for Hyper-V/WSL2 support).
2.  **Docker Desktop for Windows**: [Download & Install](https://www.docker.com/products/docker-desktop).
    - Enable WSL 2 backend during installation for better performance.

## Installation Steps

### 1. Copy Project Files

Copy the entire project folder to the target Windows machine.
**Migrating Data?** If you have existing Metabase data, read `MIGRATION.md` first.

Ensure you have the following key files:

- `docker-compose.yml`
- `Dockerfile.metabase` (Metabase)
- `Dockerfile.dataplatform`
- `.env.example`
- `ingestion/`, `transformation/`, `orchestration/`, `webhook_consumer/` folders.

_Note: An `app_data` folder will be created automatically to store all runtime data (Data Lake, Logs, DB)._

### 2. Configure Environment Variables

1.  Duplicate `.env.example` and rename it to `.env.prod`.
2.  Open `.env.prod` and fill in your real credentials:
    - **Sapo API**: Keys, secrets, store URL.
    - **Cloudflare/Worker**: URL for the webhook receiver (if applicable).
    - **Metabase DB**: Connection details for the Metabase application database (Postgres).
      - If using a local Postgres on Windows, use `MB_DB_HOST=host.docker.internal`.

### 3. Build and Run Containers

Open **PowerShell** or **Command Prompt** in the project directory.

### 3. Build and Run Containers

#### Option A: Standard (Keep .env.prod)

Run this if you manage the server securely and want easy updates:

```powershell
docker compose up -d --build --remove-orphans
```

#### Option B: High Security (Delete .env.prod)

Run this to inject variables once and immediately delete the file from disk:

```powershell
.\scripts\secure_deploy.ps1
```

- This script opens Notepad for you to paste secrets.
- Runs Docker.
- Deletes `.env.prod` automatically upon success.
- **Note**: If you run `docker compose down`, you will need to re-enter secrets to start again.

### 4. Verify Services

#### Option A: Via Command Line

Check status:

```powershell
docker compose ps
```

You should see 3 services running: `data_platform`, `webhook_consumer`, `metabase`.

#### Option B: Via Docker Desktop UI

1.  Open **Docker Desktop**.
2.  Go to the **Containers** tab.
3.  You will see a group named `data-integration2` (or your folder name).
4.  Expand it to see the 3 services (`data_platform`, `webhook_consumer`, `metabase`).
5.  Click on any container to view its **Logs**, **Inspect** variables, or **Stop/Restart** it easily with buttons.

#### Access Applications

- **Dagster UI**: [http://localhost:3001](http://localhost:3001)
- **Metabase**: [http://localhost:3000](http://localhost:3000)

## Maintenance

### Updating Code

If you modify code in `ingestion`, `transformation`, etc., you need to rebuild:

```powershell
docker compose up -d data_platform --build --remove-orphans
```

### Cleanup Old Dagster Runs

```
docker compose exec data_platform python scripts/maintenance/purge_dagster_runs.py --keep-days <số ngày> --force
```

### Viewing Logs

```powershell
docker compose logs -f
```

### Stopping Services

```powershell
docker compose down
```

To stop and remove volumes (WARNING: Deletes Metabase data if not using external DB):

```powershell
docker compose down -v
```

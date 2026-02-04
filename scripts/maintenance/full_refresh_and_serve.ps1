<#
.SYNOPSIS
    Automates the Full Refresh of the Data Warehouse and Regeneration of the Serving Layer.

.DESCRIPTION
    This script performs the following steps:
    1. Ensures the 'data_platform' Docker container is up and running.
    2. Executes a full dbt build (`--full-refresh`) to apply all schema changes and rebuild tables.
    3. Runs the `generate_serving_db.py` script to rotate the Serving Layer (DuckDB).

.EXAMPLE
    .\scripts\maintenance\full_refresh_and_serve.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host ">>> [1/3] Ensuring 'data_platform' container is running..." -ForegroundColor Cyan
docker compose up -d data_platform

Write-Host "`n>>> [2/3] Running dbt Full Refresh (This may take a while)..." -ForegroundColor Cyan
# Using --select tag:staging tag:standard tag:mart to target main layers, or omit for pure full build
docker exec data_platform dbt build --project-dir transformation --full-refresh

if ($LASTEXITCODE -ne 0) {
    Write-Error "dbt build failed! Aborting."
}

Write-Host "`n>>> [3/3] Regenerating Serving Layer (DuckDB)..." -ForegroundColor Cyan
docker exec data_platform python scripts/provisioning/generate_serving_db.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Serving generation failed!"
}

Write-Host "`n>>> SUCCESS: Full Refresh & Serving Update Complete." -ForegroundColor Green

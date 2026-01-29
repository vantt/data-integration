$ScriptDir = Split-Path $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Set DBT Environment Variables
# Pointing to data_lake/export/marts
$Env:DAGSTER_HOME = "$ScriptDir\app_data\dagster_home"
$Env:DAGSTER_PORT = "3001"
$Env:DBT_EXPORT_PATH = "$ScriptDir\app_data\data_lake\export\marts"
$Env:DBT_DATA_LAKE_PATH = "$ScriptDir\app_data\data_lake"

Write-Host "-> Starting Dagster Dev Server..." -ForegroundColor Cyan

# Check if venv exists
$VenvPath = "$ScriptDir\ingestion\venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "   Activating virtual environment..." -ForegroundColor Green
    & $VenvPath
}
else {
    Write-Host "   WARNING: Virtual environment not found at $VenvPath" -ForegroundColor Yellow
}

# Run Dagster
if (-not (Test-Path $Env:DAGSTER_HOME)) {
    New-Item -ItemType Directory -Force -Path $Env:DAGSTER_HOME | Out-Null
}

Write-Host "-> DAGSTER_HOME: $Env:DAGSTER_HOME" -ForegroundColor Cyan

# Kill any existing dbt/python processes to release locks (Aggressive Cleanup)
Write-Host "-> Cleaning up old Python processes..." -ForegroundColor Gray
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*venv*" } | Stop-Process -Force
Get-Process dbt -ErrorAction SilentlyContinue | Stop-Process -Force

# Clean up stale dbt locks
$DbtLockFile = "$ScriptDir\transformation\target\manifest.concurrent-update-lock"
if (Test-Path $DbtLockFile) {
    Write-Host "-> Removing stale dbt lock file..." -ForegroundColor Yellow
    Remove-Item -Path $DbtLockFile -Force
}

# Pre-parse DBT Manifest (Single Threaded to avoid race conditions later)
Write-Host "-> Pre-parsing dbt project..." -ForegroundColor Cyan
Set-Location "$ScriptDir\ingestion"
$DbtExe = "$ScriptDir\ingestion\venv\Scripts\dbt.exe"
& $DbtExe parse --project-dir "$ScriptDir\transformation" --profiles-dir "$ScriptDir\transformation"
Set-Location $ScriptDir

Write-Host "-> Running dagster dev..." -ForegroundColor Green
dagster dev -f orchestration/definitions.py -p $Env:DAGSTER_PORT

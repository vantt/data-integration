$ScriptDir = Split-Path $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "🚀 Starting Dagster Dev Server..." -ForegroundColor Cyan

# Check if venv exists
$VenvPath = "$ScriptDir\dlt\venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "   Activating virtual environment..." -ForegroundColor Green
    & $VenvPath
} else {
    Write-Host "⚠️  Virtual environment not found at $VenvPath" -ForegroundColor Yellow
}

# Run Dagster
$Env:DAGSTER_HOME = "$ScriptDir\.dagster_home"
if (-not (Test-Path $Env:DAGSTER_HOME)) {
    New-Item -ItemType Directory -Force -Path $Env:DAGSTER_HOME | Out-Null
}

Write-Host "   Running dagster dev..." -ForegroundColor Green
dagster dev -f orchestration/definitions.py

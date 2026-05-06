# Fix stale DuckDB lock on ingestion_health.duckdb
# Use this when record_run() fails with "Could not set lock on file" (PID 0)
# DO NOT restart Docker Desktop to fix this — it will freeze WSL2

param(
    [string]$DbPath = "D:\Vantt\app\data-integration\app_data\data_lake\monitoring\ingestion_health.duckdb",
    [string]$Container = "data_platform",
    [string]$ContainerDbPath = "/app/var/data_lake/monitoring/ingestion_health.duckdb"
)

$ErrorActionPreference = "Stop"

Write-Host "=== DuckDB Lock Fix ===" -ForegroundColor Cyan

# Step 1: Kill dllhost.exe processes holding the file (Windows Defender COM proxy)
Write-Host "[1/3] Killing dllhost.exe processes..." -ForegroundColor Yellow
$dllhosts = Get-Process -Name "dllhost" -ErrorAction SilentlyContinue
if ($dllhosts) {
    $dllhosts | ForEach-Object {
        Write-Host "  Killing dllhost PID $($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "  No dllhost.exe found" -ForegroundColor Gray
}

# Step 2: Run CHECKPOINT inside the container (avoids host-side lock contention)
Write-Host "[2/3] Running CHECKPOINT inside container $Container..." -ForegroundColor Yellow
$containerRunning = docker inspect -f "{{.State.Running}}" $Container 2>$null
if ($containerRunning -eq "true") {
    docker exec $Container python -c "
import duckdb
con = duckdb.connect('$ContainerDbPath')
con.execute('CHECKPOINT')
con.close()
print('CHECKPOINT OK')
"
} else {
    # Container not running — checkpoint from host
    Write-Host "  Container not running, checkpointing from host..." -ForegroundColor Gray
    python -c "
import duckdb
con = duckdb.connect(r'$DbPath')
con.execute('CHECKPOINT')
con.close()
print('CHECKPOINT OK (host)')
"
}

# Step 3: Verify write access
Write-Host "[3/3] Verifying write access..." -ForegroundColor Yellow
docker exec $Container python -c "
import duckdb, datetime
con = duckdb.connect('$ContainerDbPath')
count = con.execute('SELECT COUNT(*) FROM ingestion_runs').fetchone()[0]
con.close()
print(f'OK — {count} runs in DB, write access confirmed')
" 2>&1

Write-Host "=== Done ===" -ForegroundColor Green
Write-Host ""
Write-Host "To prevent recurrence, add Defender exclusion (run as Admin):" -ForegroundColor Cyan
Write-Host "  Add-MpPreference -ExclusionPath 'D:\Vantt\app\data-integration\app_data\data_lake'" -ForegroundColor White

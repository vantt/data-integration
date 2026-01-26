$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$ExportBaseDir = "$ProjectRoot\data_lake\export\marts"

# 1. Generate Timestamp
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$VersionDirName = "v_$Timestamp"
$FullExportPath = "$ExportBaseDir\$VersionDirName"

Write-Host "[Pipeline] Starting Zero-Downtime Deployment"
Write-Host "[Pipeline] Version: $VersionDirName"

# 2. Create Directory
if (-not (Test-Path $FullExportPath)) {
    Write-Host "[Pipeline] Creating Export Directory: $FullExportPath"
    New-Item -ItemType Directory -Force -Path $FullExportPath | Out-Null
}

# 2.1 Cleanup Old Versions (Keep last 5)
$KeepVersions = 5
Write-Host "[Pipeline] Checking for old versions to cleanup (Keep: $KeepVersions)..."
$AllVersions = Get-ChildItem -Path $ExportBaseDir -Directory -Filter "v_*" | Sort-Object Name -Descending

if ($AllVersions.Count -gt $KeepVersions) {
    $VersionsToRemove = $AllVersions | Select-Object -Skip $KeepVersions
    foreach ($v in $VersionsToRemove) {
        Write-Host "[Pipeline] Removing old version: $($v.Name)"
        Remove-Item -Path $v.FullName -Recurse -Force
    }
}
else {
    Write-Host "[Pipeline] Version count ($($AllVersions.Count)) is within limit."
}

# 2b. Create Symbolic Link / Junction for Cross-Compatibility
# Map D:\data_lake -> Current Project data_lake
$GlobalDataLake = "D:\data_lake"
$LocalDataLake = "$ProjectRoot\data_lake"
if (-not (Test-Path $GlobalDataLake)) {
    Write-Host "[Pipeline] Creating Junction $GlobalDataLake -> $LocalDataLake"
    cmd /c mklink /J "$GlobalDataLake" "$LocalDataLake" | Out-Null
}
elseif ((Get-Item $GlobalDataLake).Target -ne $LocalDataLake) {
    Write-Warning "D:\data_lake exists. Ensuring it points to project..."
}

# 3. Set Environment Variable for dbt
$env:DBT_EXPORT_PATH = $FullExportPath
$env:DBT_DATA_LAKE_PATH = "$ProjectRoot\data_lake"

# 4. Resolve Python Environment (Use dlt venv)
$PythonCmd = "python"
if (Test-Path "$ProjectRoot\dlt\venv\Scripts\python.exe") {
    $PythonCmd = "$ProjectRoot\dlt\venv\Scripts\python.exe"
}
Write-Host "[Pipeline] Using Python Executable: $PythonCmd"

# 5. Run dbt Build (via wrapper script)
Write-Host "[Pipeline] Execution dbt build via wrapper..."
$DbtWrapper = "$ProjectRoot\transformation\scripts\run_dbt.py"

& $PythonCmd $DbtWrapper --select +tag:mart
if ($LASTEXITCODE -ne 0) {
    Write-Error "dbt build failed!"
}

# 6. Run Serving Update (with Lock handling)
Write-Host "[Pipeline] Identifying Metabase Container..."
# Robust method: Get ID and Image, filter in PowerShell
$Containers = docker ps --format "{{.ID}} {{.Image}}"
$MetabaseId = $null
foreach ($line in $Containers) {
    if ($line -match "metabase") {
        $MetabaseId = $line.Split(" ")[0]
        break
    }
}

if ($MetabaseId) {
    Write-Host "[Pipeline] Stopping Metabase ($MetabaseId) to release DB lock..."
    docker stop $MetabaseId | Out-Null
}

Write-Host "[Pipeline] Updating Serving Layer..."
Set-Location "$ProjectRoot"
python scripts/provisioning/generate_serving_db.py

if ($MetabaseId) {
    Write-Host "[Pipeline] Restarting Metabase..."
    docker start $MetabaseId | Out-Null
    Write-Host "[Pipeline] Metabase restarted."
}

Write-Host "[Pipeline] Deployment Completed Successfully."

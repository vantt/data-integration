param(
    # TECHNIQUE: "Argument Passthrough"
    # Using ValueFromRemainingArguments allows us to capture ALL arguments (like --select, --full-refresh)
    # properly without PowerShell mistakenly parsing them as partial parameter matches.
    # This acts as a robust proxy to the underlying Python script.
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PassthroughArgs
)

# Default to running marts if no args provided
if ($null -eq $PassthroughArgs -or $PassthroughArgs.Count -eq 0) {
    Write-Host "[Pipeline] No arguments provided. Defaulting to: --select +tag:mart"
    $PassthroughArgs = @("--select", "+tag:mart")
}
else {
    Write-Host "[Pipeline] Passing arguments to dbt: $($PassthroughArgs -join ' ')"
}

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$ExportBaseDir = "$ProjectRoot\data_lake\export\marts"

# 2. Generate Version Path via Shared Python Utility
Write-Host "[Pipeline] Resolving version path via shared utility..."
$VersionManager = "$ProjectRoot\scripts\utils\version_manager.py"
$PythonCmd = "python"
if (Test-Path "$ProjectRoot\dlt\venv\Scripts\python.exe") {
    $PythonCmd = "$ProjectRoot\dlt\venv\Scripts\python.exe"
}

# Call utility to Create + Cleanup (Keep 5)
$FullExportPath = & $PythonCmd $VersionManager --action create_and_cleanup --base-dir $ExportBaseDir --keep 5
# Trim whitespace just in case
$FullExportPath = $FullExportPath.Trim()

if (-not $FullExportPath) {
    Write-Error "Failed to generate export path from version_manager.py"
}

Write-Host "[Pipeline] Target Export (Versioned): $FullExportPath"
$VersionDirName = Split-Path $FullExportPath -Leaf

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

& $PythonCmd $DbtWrapper $PassthroughArgs
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

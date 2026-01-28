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

# 2. Export Path (Stable Rolling)
Write-Host "[Pipeline] Setting Export Path to Rolling Directory..."
$FullExportPath = "$ExportBaseDir\rolling"
if (-not (Test-Path $FullExportPath)) {
    New-Item -ItemType Directory -Force -Path $FullExportPath | Out-Null
}

Write-Host "[Pipeline] Target Export (Stable): $FullExportPath"
$VersionDirName = "rolling"

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
if (Test-Path "$ProjectRoot\ingestion\venv\Scripts\python.exe") {
    $PythonCmd = "$ProjectRoot\ingestion\venv\Scripts\python.exe"
}
Write-Host "[Pipeline] Using Python Executable: $PythonCmd"

# 5. Run dbt Build (via wrapper script)
Write-Host "[Pipeline] Execution dbt build via wrapper..."
$DbtWrapper = "$ProjectRoot\transformation\scripts\run_dbt.py"

& $PythonCmd $DbtWrapper $PassthroughArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "dbt build failed!"
}

# 6. Run Serving Update (Rolling Snapshot / Zero Downtime)
Write-Host "[Pipeline] Updating Serving Layer (Rolling Mode)..."
Set-Location "$ProjectRoot"
python scripts/provisioning/generate_serving_db.py

Write-Host "[Pipeline] Deployment Completed Successfully."

Write-Host "[Pipeline] Deployment Completed Successfully."

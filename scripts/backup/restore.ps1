# =============================================================================
# Data Integration Platform - Restore Script
# =============================================================================
# Restores from a backup created by backup.ps1.
#
# Usage:
#   .\restore.ps1 -BackupDir "D:\...\backups\20260404-020000"
#   .\restore.ps1 -BackupDir "D:\...\backups\20260404-020000" -DryRun
#   .\restore.ps1 -BackupDir "D:\...\backups\20260404-020000" -Force  # skip confirmation prompt
# =============================================================================

param(
    [Parameter(Mandatory)]
    [string]$BackupDir,
    [string]$ProjectRoot = "D:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2",
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ExitCode = 0
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupRoot = Split-Path $BackupDir -Parent
$LogFile    = Join-Path $BackupRoot "restore-$Timestamp.log"

function Log {
    param([string]$Message)
    $entry = "$(Get-Date -Format 'HH:mm:ss') $Message"
    Write-Host $entry
    Add-Content -Path $LogFile -Value $entry
}

# --- Validate ---
if (-not (Test-Path $BackupDir)) {
    Write-Error "Backup directory not found: $BackupDir"
    exit 1
}

if (-not (Test-Path (Join-Path $ProjectRoot "docker-compose.yml"))) {
    Write-Error "docker-compose.yml not found in $ProjectRoot — is ProjectRoot correct?"
    exit 1
}

$appDataBackup = Join-Path $BackupDir "app_data"
if (-not (Test-Path $appDataBackup)) {
    Write-Error "No app_data found in backup: $BackupDir"
    exit 1
}

Log "=== Restore from: $BackupDir ==="
Log "Target: $ProjectRoot"

if ($DryRun) {
    Log "DRY RUN - no changes will be made"
}

# --- Show backup contents ---
$size = (Get-ChildItem $appDataBackup -Recurse -File | Measure-Object -Property Length -Sum).Sum
$sizeMB = [math]::Round($size / 1MB, 1)
Log "Backup size: ${sizeMB}MB"

$dirs = Get-ChildItem $appDataBackup -Directory | ForEach-Object { $_.Name }
Log "Contains: $($dirs -join ', ')"

# --- Confirm ---
if (-not $DryRun) {
    if ($Force) {
        Log "Force flag set — skipping confirmation."
    } else {
        $confirm = Read-Host "This will STOP containers and OVERWRITE app_data. Continue? (yes/no)"
        if ($confirm -ne "yes") {
            Log "Aborted."
            exit 0
        }
    }
}

if ($DryRun) {
    Log "Would stop containers, robocopy $appDataBackup -> $(Join-Path $ProjectRoot 'app_data'), then restart."
    Log "DRY RUN complete."
    exit 0
}

# --- Stop containers, restore, restart (with safe Push/Pop) ---
Log "Stopping containers..."
Push-Location $ProjectRoot
try {
    docker compose stop
    if ($LASTEXITCODE -ne 0) {
        Log "WARNING: docker compose stop exited with code $LASTEXITCODE"
        Log "Proceeding with restore (data may be inconsistent)."
    } else {
        Log "Containers stopped."
    }

    # --- Restore app_data ---
    $appDataDst = Join-Path $ProjectRoot "app_data"
    Log "Restoring app_data..."
    robocopy $appDataBackup $appDataDst /MIR /MT:4 /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -ge 8) {
        Log "ERROR: robocopy failed with exit code $LASTEXITCODE"
        Log "WARNING: app_data may be in a PARTIAL state — do not rely on this data until a clean restore succeeds."
        $ExitCode = 1
    }

    # --- Restore config files (optional, manual) ---
    $configBackup = Join-Path $BackupDir "config"
    if (Test-Path $configBackup) {
        Log "Config files available at: $configBackup"
        Log "Restore them manually if needed (they may contain different env settings)."
    }
} finally {
    # --- Always restart ---
    Log "Starting containers..."
    docker compose start
    if ($LASTEXITCODE -ne 0) {
        Log "ERROR: Failed to start containers (exit code $LASTEXITCODE)"
        Log "Run manually: cd $ProjectRoot && docker compose start"
        $ExitCode = 1
    } else {
        Log "Containers started."
    }
    Pop-Location
}

if ($ExitCode -eq 0) {
    Log "=== Restore complete ==="
} else {
    Log "=== Restore completed WITH ERRORS ==="
}
exit $ExitCode

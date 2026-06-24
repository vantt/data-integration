# =============================================================================
# Data Integration Platform - Automated Backup Script
# =============================================================================
# Backs up all persistent data (data_lake, metabase, dagster) with container
# stop/start for consistency. Designed for Windows Task Scheduler.
#
# Usage:
#   .\backup.ps1                          # Use defaults
#   .\backup.ps1 -BackupRoot "E:\backups" # Custom backup location
#   .\backup.ps1 -KeepCount 14           # Keep 14 backups instead of 7
#   .\backup.ps1 -SkipRestart            # Don't restart after backup (maintenance)
# =============================================================================

param(
    [string]$ProjectRoot = $(if ($env:BACKUP_PROJECT_ROOT) { $env:BACKUP_PROJECT_ROOT } else { "D:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2" }),
    [string]$BackupRoot  = $(if ($env:BACKUP_ROOT) { $env:BACKUP_ROOT } else { "D:\_1.FWG_PARA\1.Projects\dev\dataware_house\backups" }),
    [int]$KeepCount      = $(if ($env:BACKUP_KEEP_COUNT) { [int]$env:BACKUP_KEEP_COUNT } else { 7 }),
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $BackupRoot $Timestamp
$LogFile   = Join-Path $BackupRoot "backup-$Timestamp.log"
$ExitCode  = 0
$BackupDataSucceeded = $false

# --- Pre-flight checks ---
if ($KeepCount -lt 1) {
    Write-Error "KeepCount must be at least 1 (got $KeepCount)"
    exit 1
}

if (-not (Test-Path (Join-Path $ProjectRoot "docker-compose.yml"))) {
    Write-Error "docker-compose.yml not found in $ProjectRoot"
    exit 1
}

# Ensure backup root exists before first log write
try {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
} catch {
    Write-Error "Failed to create backup directory '$BackupDir': $($_.Exception.Message)"
    exit 1
}

function Log {
    param([string]$Message)
    $entry = "$(Get-Date -Format 'HH:mm:ss') $Message"
    Write-Host $entry
    try { Add-Content -Path $LogFile -Value $entry } catch { <# disk full / permissions — console output still works #> }
}

Log "=== Backup started: $Timestamp ==="
Log "Source: $ProjectRoot"
Log "Destination: $BackupDir"

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# --- Step 1: Stop containers, backup, restart (with safe Push/Pop) ---
Push-Location $ProjectRoot
try {
    Log "Stopping containers..."
    docker compose stop
    if ($LASTEXITCODE -ne 0) {
        Log "WARNING: docker compose stop exited with code $LASTEXITCODE"
        Log "Proceeding with hot backup (may be inconsistent for H2 DB)."
    } else {
        Log "Containers stopped."
    }

    # --- Step 2: Backup app_data (the critical data) ---
    $appDataSrc = Join-Path $ProjectRoot "app_data"
    $appDataDst = Join-Path $BackupDir "app_data"

    if (Test-Path $appDataSrc) {
        Log "Backing up app_data..."
        # /MIR = mirror, /MT:4 = 4 threads, /R:1 = 1 retry, /W:1 = 1s wait
        # /NFL /NDL /NJH /NJS = minimal output
        robocopy $appDataSrc $appDataDst /MIR /MT:4 /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
        # robocopy returns 0-7 for success, 8+ for errors
        if ($LASTEXITCODE -ge 8) {
            Log "ERROR: robocopy failed with exit code $LASTEXITCODE"
            $ExitCode = 1
        } else {
            $BackupDataSucceeded = $true
            try {
                $size = (Get-ChildItem $appDataDst -Recurse -File | Measure-Object -Property Length -Sum).Sum
                $sizeMB = [math]::Round(([long](if ($null -eq $size) { 0 } else { $size })) / 1MB, 1)
                Log "app_data backed up: ${sizeMB}MB"
            } catch {
                Log "app_data backed up (size unavailable: $($_.Exception.Message))"
            }
        }
    } else {
        Log "WARNING: app_data not found at $appDataSrc"
        $ExitCode = 1
    }

    # --- Step 3: crm_data backup — DISABLED (deprecated) ---
    # A raw `cp -a` of the live crm_data volume is WAL-unsafe (torn SQLite snapshot).
    # CRM is now backed up by crm/ops/backup_crm.py — a verified, consistent SQLite
    # online-backup snapshot written to the `crm_backups` volume. See
    # crm/docs/backup-restore-runbook.md. Do NOT re-enable this raw copy.
    Log "crm_data raw copy SKIPPED — handled by crm/ops/backup_crm.py (verified snapshot)"

    # --- Step 4: Backup config files ---
    Log "Backing up config files..."
    $configDst = Join-Path $BackupDir "config"
    try {
        New-Item -ItemType Directory -Path $configDst -Force | Out-Null

        $configFiles = @(".env.docker", "docker-compose.yml", "Dockerfile.dataplatform", "Dockerfile.metabase")
        $copiedCount = 0
        foreach ($f in $configFiles) {
            $src = Join-Path $ProjectRoot $f
            if (Test-Path $src) {
                try {
                    Copy-Item $src -Destination $configDst
                    $copiedCount++
                } catch {
                    Log "WARNING: Could not copy config file '$f': $($_.Exception.Message)"
                }
            }
        }
        if ($copiedCount -gt 0) {
            Log "Config files backed up ($copiedCount of $($configFiles.Count) found)."
        } else {
            Log "WARNING: No config files found to back up (checked: $($configFiles -join ', '))."
        }
    } catch {
        Log "WARNING: Config backup skipped — could not create config dir: $($_.Exception.Message)"
    }
} finally {
    # --- Step 5: Always restart containers (unless SkipRestart) ---
    # Wrapped in try/catch so a thrown error (e.g. docker not on PATH) never
    # prevents Pop-Location from running and stranding the shell in $ProjectRoot.
    if (-not $SkipRestart) {
        Log "Starting containers..."
        try {
            docker compose start
            if ($LASTEXITCODE -ne 0) {
                Log "ERROR: Failed to start containers (exit code $LASTEXITCODE)"
                Log "Run manually: cd $ProjectRoot && docker compose start"
                $ExitCode = 1
            } else {
                Log "Containers started."
            }
        } catch {
            Log "ERROR: docker compose start threw an exception: $($_.Exception.Message)"
            Log "Run manually: cd $ProjectRoot && docker compose start"
            $ExitCode = 1
        }
    } else {
        Log "SkipRestart flag set. Containers remain stopped."
    }
    Pop-Location
}

# --- Step 6: Remove failed backup directory to avoid polluting rotation ---
$BackupDirRemoved = $false
if (-not $BackupDataSucceeded) {
    try {
        Remove-Item $BackupDir -Recurse -Force
        Log "Removed failed/empty backup directory: $BackupDir"
        $BackupDirRemoved = $true
    } catch {
        Log "WARNING: Could not remove failed backup directory '$BackupDir': $($_.Exception.Message)"
        Log "WARNING: The failed directory will be excluded from rotation counts but remains on disk — remove it manually when possible."
    }
}

# --- Step 7: Rotate old backups ---
Log "Rotating backups (keeping last $KeepCount)..."
try {
    $allBackups = Get-ChildItem -Path $BackupRoot -Directory |
        Where-Object { $_.Name -match '^\d{8}-\d{6}$' } |
        Sort-Object Name -Descending

    # If this run's backup dir is still on disk but contains no valid data, exclude it from
    # rotation so it cannot displace a real backup from the kept set.
    if (-not $BackupDataSucceeded -and -not $BackupDirRemoved) {
        $allBackups = @($allBackups | Where-Object { $_.FullName -ne $BackupDir })
    }

    if ($allBackups.Count -gt $KeepCount) {
        $toDelete = $allBackups | Select-Object -Skip $KeepCount
        foreach ($old in $toDelete) {
            try {
                Remove-Item $old.FullName -Recurse -Force
                Log "Deleted old backup: $($old.Name)"
            } catch {
                Log "WARNING: Could not delete old backup '$($old.Name)': $($_.Exception.Message)"
                $ExitCode = 1
            }
        }
    }
} catch {
    Log "WARNING: Could not enumerate backups for rotation: $($_.Exception.Message)"
    $ExitCode = 1
}

# Clean old log files too (keep matching backup count) — covers both backup-*.log and restore-*.log
foreach ($logPattern in @("backup-*.log", "restore-*.log")) {
    try {
        $allLogs = Get-ChildItem -Path $BackupRoot -Filter $logPattern | Sort-Object Name -Descending
        if ($allLogs.Count -gt $KeepCount) {
            $allLogs | Select-Object -Skip $KeepCount | ForEach-Object {
                try {
                    Remove-Item $_.FullName -Force
                } catch {
                    Log "WARNING: Could not delete old log '$($_.Name)': $($_.Exception.Message)"
                }
            }
        }
    } catch {
        Log "WARNING: Could not enumerate logs for rotation ($logPattern): $($_.Exception.Message)"
    }
}

$stopwatch.Stop()
if ($ExitCode -eq 0) {
    Log "=== Backup completed successfully in $([math]::Round($stopwatch.Elapsed.TotalSeconds, 1))s ==="
    Log "Backup location: $BackupDir"
} else {
    Log "=== Backup completed WITH ERRORS in $([math]::Round($stopwatch.Elapsed.TotalSeconds, 1))s ==="
    if ($BackupDataSucceeded) {
        Log "Backup location: $BackupDir"
    } elseif ($BackupDirRemoved) {
        Log "Failed backup directory was removed (no valid data)."
    } else {
        Log "Failed backup directory could NOT be removed — remove it manually when possible (excluded from rotation counts)."
    }
}
exit $ExitCode

# =============================================================================
# Register backup as a Windows Scheduled Task (run as Admin)
# =============================================================================
# Creates a daily task at 2:00 AM to run backup.ps1 automatically.
#
# Usage (run as Administrator):
#   .\setup-task-scheduler.ps1
#   .\setup-task-scheduler.ps1 -Time "03:00"                  # Change time
#   .\setup-task-scheduler.ps1 -ProjectRoot "E:\myproject"    # Override project path
#   .\setup-task-scheduler.ps1 -BackupRoot "E:\backups"       # Override backup destination
#   .\setup-task-scheduler.ps1 -KeepCount 14                  # Keep 14 backups
#   .\setup-task-scheduler.ps1 -Unregister                    # Remove the task
# =============================================================================

param(
    [string]$Time       = "02:00",
    [string]$ProjectRoot = "D:\_1.FWG_PARA\1.Projects\dev\dataware_house\data-integration2",
    [string]$BackupRoot  = "D:\_1.FWG_PARA\1.Projects\dev\dataware_house\backups",
    [int]$KeepCount      = 7,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$TaskName = "DataIntegration-Backup"
$ScriptPath = Join-Path $PSScriptRoot "backup.ps1"

# Require elevated privileges to register scheduled tasks
$currentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator to register a scheduled task."
    exit 1
}

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Task '$TaskName' removed."
    exit 0
}

if (-not (Test-Path $ScriptPath)) {
    Write-Error "backup.ps1 not found at $ScriptPath"
    exit 1
}

# Remove existing task if any
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$BackupArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" +
              " -ProjectRoot `"$ProjectRoot`"" +
              " -BackupRoot `"$BackupRoot`"" +
              " -KeepCount $KeepCount"

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $BackupArgs `
    -WorkingDirectory $PSScriptRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily backup of Data Integration Platform (app_data + config)" `
    -RunLevel Highest

Write-Host ""
Write-Host "Scheduled task '$TaskName' created successfully!"
Write-Host "  Schedule:    Daily at $Time"
Write-Host "  Script:      $ScriptPath"
Write-Host "  ProjectRoot: $ProjectRoot"
Write-Host "  BackupRoot:  $BackupRoot"
Write-Host "  KeepCount:   $KeepCount"
Write-Host ""
Write-Host "Verify with: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Test run:    Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "IMPORTANT: Task is registered for user '$env:USERNAME' (run only when logged on)."
Write-Host "  For true unattended overnight backups, open Task Scheduler, edit '$TaskName',"
Write-Host "  and set 'Run whether user is logged on or not' with stored credentials."

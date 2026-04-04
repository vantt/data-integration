# =============================================================================
# Register backup as a Windows Scheduled Task (run as Admin)
# =============================================================================
# Creates a daily task at 2:00 AM to run backup.ps1 automatically.
#
# Usage (run as Administrator):
#   .\setup-task-scheduler.ps1
#   .\setup-task-scheduler.ps1 -Time "03:00"     # Change time
#   .\setup-task-scheduler.ps1 -Unregister        # Remove the task
# =============================================================================

param(
    [string]$Time = "02:00",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$TaskName = "DataIntegration-Backup"
$ScriptPath = Join-Path $PSScriptRoot "backup.ps1"

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

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
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
Write-Host "  Schedule: Daily at $Time"
Write-Host "  Script:   $ScriptPath"
Write-Host ""
Write-Host "Verify with: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Test run:    Start-ScheduledTask -TaskName '$TaskName'"

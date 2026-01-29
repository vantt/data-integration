# Secure Deployment Script
# 1. Ensures .env.prod exists (or prompts to create it).
# 2. Runs Docker Compose.
# 3. Securely deletes .env.prod immediately after.

$ErrorActionPreference = "Stop"

$EnvFile = ".env.prod"
$ExampleFile = ".env.example"

Write-Host "-> Starting Secure Deployment..." -ForegroundColor Cyan

# 1. Check Env File
if (-not (Test-Path $EnvFile)) {
    Write-Host "   '$EnvFile' not found." -ForegroundColor Yellow
    Write-Host "   Creating temporary '$EnvFile' from example..."
    Copy-Item $ExampleFile $EnvFile
    
    # Open Notepad for user to paste secrets
    Write-Host "   Opening Notepad. PLEASE PASTE YOUR SECRETS/CONFIG NOW." -ForegroundColor Yellow
    Write-Host "   Save and Close Notepad to continue..." -ForegroundColor Yellow
    Start-Process notepad.exe $EnvFile -Wait
}

# 2. Run Docker Compose
Write-Host "-> Running Docker Compose (Build & Up)..." -ForegroundColor Cyan
try {
    docker compose up -d --build
    Write-Host "-> Deployment Successful!" -ForegroundColor Green
}
catch {
    Write-Host "-> Deployment Failed!" -ForegroundColor Red
    Write-Host "   Config file is preserved for debugging at: $EnvFile"
    exit 1
}

# 3. Clean Up
Write-Host "-> Cleaning up secrets..." -ForegroundColor Cyan
Remove-Item $EnvFile -Force
Write-Host "   '$EnvFile' has been deleted." -ForegroundColor Green
Write-Host "   Containers are running with injected variables."
Write-Host "   FUTURE NOTE: Running 'docker compose restart' works, but 'down'/'up' will require re-entering secrets." -ForegroundColor Gray

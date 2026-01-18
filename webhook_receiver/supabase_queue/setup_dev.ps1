# Check if Supabase CLI is installed
if (-not (Get-Command supabase -ErrorAction SilentlyContinue)) {
    Write-Host "Supabase CLI is not installed. Installing via Scoop..." -ForegroundColor Yellow
    scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
    scoop install supabase
}

# Check Supabase version
supabase --version

# Start Supabase locally
Write-Host "Starting Supabase local stack..." -ForegroundColor Cyan
supabase start

# Apply migrations (this effectively resets and applies if using db reset, or just pushes if using db push not in local)
# For local dev, we want to ensure state matches migrations.
Write-Host "Resetting local database to match migrations..." -ForegroundColor Cyan
supabase db reset

Write-Host "Setup complete! API and Studio are ready." -ForegroundColor Green
Write-Host "Studio URL: http://127.0.0.1:54323"

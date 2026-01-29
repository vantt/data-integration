@echo off
REM Helper script to run DBT commands inside the Docker container
REM usage: ./dbt_docker.bat build --select +my_model

echo -> Executing dbt in data_platform container...
echo -> Running directory check...
docker compose exec -T data_platform python /app/scripts/ensure_dbt_directories.py
docker compose exec data_platform dbt %*

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] dbt command failed.
    exit /b %ERRORLEVEL%
)
echo [SUCCESS] dbt command finished.

"""Pytest configuration for data-integration tests.

Sets required environment variables before any test imports.
This runs before test collection, ensuring modules that check
env vars at import time won't fail.
"""
import os
import tempfile

# Set env vars BEFORE any test module imports
# These are test-only defaults - production must set via .env.docker/.env.local

def pytest_configure(config):
    """Set test environment variables before collection."""
    # Use temp directory for test data lake (isolated from real data)
    test_data_lake = os.path.join(tempfile.gettempdir(), "test_data_lake")
    os.makedirs(test_data_lake, exist_ok=True)

    # Only set if not already set (allow override via shell env)
    if "DBT_DATA_LAKE_PATH" not in os.environ:
        os.environ["DBT_DATA_LAKE_PATH"] = test_data_lake

    if "INGESTION_HEALTH_DB" not in os.environ:
        os.environ["INGESTION_HEALTH_DB"] = os.path.join(
            test_data_lake, "monitoring", "test_ingestion_health.duckdb"
        )

"""
config.py — environment configuration for the CRM reverse-ETL sync.

Environment variables:
  CRM_OLAP_PATH  — path to olap.duckdb (production warehouse).
                   Falls back to sapo_export_latest.duckdb in the same dir.
  CRM_CACHE_DB   — path to cache.db SQLite file (default: crm/data/cache.db).
"""

import os
import pathlib

# Root of the repo (two levels up from crm/sync/).
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Default warehouse DuckDB path; override via CRM_OLAP_PATH.
_DEFAULT_OLAP = str(_REPO_ROOT / "data" / "olap.duckdb")

# Default cache.db path; override via CRM_CACHE_DB.
_DEFAULT_CACHE = str(pathlib.Path(__file__).resolve().parent.parent / "data" / "cache.db")


def olap_path() -> str:
    """Return the resolved path to the warehouse DuckDB file."""
    return os.environ.get("CRM_OLAP_PATH", _DEFAULT_OLAP)


def cache_db_path() -> str:
    """Return the resolved path to cache.db."""
    return os.environ.get("CRM_CACHE_DB", _DEFAULT_CACHE)


def olap_fallback_path() -> str:
    """Return the fallback path (sapo_export_latest.duckdb) in the same dir as olap_path."""
    primary = olap_path()
    return str(pathlib.Path(primary).parent / "sapo_export_latest.duckdb")

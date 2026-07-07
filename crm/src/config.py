"""Application settings (composition-root layer).

Reads from environment so the service runs unchanged on Windows-dev and Linux-container.
No domain logic here.

Env vars:
  CRM_DATA_DIR      — directory holding crm.db and cache.db (default: ./data)
  CRM_PORT          — HTTP listen port (default: 8090)
  CRM_OLAP_PATH     — read-only DuckDB serving DB (default: /app/var/data_lake/serving/olap.duckdb)
  CRM_CACHE_DB      — warehouse read-cache SQLite path (default: {CRM_DATA_DIR}/cache.db)
  CRM_REFRESH_TOKEN — optional bearer token for /admin/refresh (default: "")
  TZ                — display timezone (default: Asia/Ho_Chi_Minh)
"""
from __future__ import annotations

import os


def _data_dir() -> str:
    return os.environ.get("CRM_DATA_DIR", "./data")


def crm_db_path() -> str:
    """Absolute-or-relative path to the owned CRM SQLite database."""
    return os.path.join(_data_dir(), "crm.db")


def cache_db_path() -> str:
    """Path to the warehouse read-cache SQLite database (wh_* tables)."""
    default = os.path.join(_data_dir(), "cache.db")
    return os.environ.get("CRM_CACHE_DB", default)


def olap_path() -> str:
    """Path to the read-only DuckDB serving database (olap.duckdb)."""
    return os.environ.get(
        "CRM_OLAP_PATH", "/app/var/data_lake/serving/olap.duckdb"
    )


def server_port() -> int:
    """HTTP listen port for the sync/admin service."""
    return int(os.environ.get("CRM_PORT", "8090"))


def refresh_token() -> str:
    """Optional bearer token that guards /admin/refresh. Empty string disables auth."""
    return os.environ.get("CRM_REFRESH_TOKEN", "")


def app_tz() -> str:
    """Display timezone for ICT formatting at the serving layer."""
    return os.environ.get("TZ", "Asia/Ho_Chi_Minh")


import json as _json


def cf_access_audience() -> str:
    """CF Access application audience tag. Empty = bypass (dev mode)."""
    return os.environ.get("CF_ACCESS_AUDIENCE", "")


def cf_team_domain() -> str:
    """Cloudflare team domain, e.g. 'myteam.cloudflareaccess.com'."""
    return os.environ.get("CF_TEAM_DOMAIN", "")


def cf_dept_claim() -> str:
    """Dot-separated JWT claim path for Lark departments (array). E.g. 'custom.departments'."""
    return os.environ.get("CF_DEPT_CLAIM", "custom.departments")


def cf_func_role_claim() -> str:
    """Dot-separated JWT claim path for Lark functional roles (array). E.g. 'custom.functional_roles'."""
    return os.environ.get("CF_FUNC_ROLE_CLAIM", "custom.functional_roles")


def cf_role_map() -> dict:
    """JSON mapping: Lark department/functional_role value → CRM role string.

    Applied to every value from CF_DEPT_CLAIM and CF_FUNC_ROLE_CLAIM; the
    highest-privilege match wins when several values map to different roles.
    Example env: CF_ROLE_MAP={"Admin":"admin","Manager":"manager","Sales":"sales"}
    """
    raw = os.environ.get("CF_ROLE_MAP", "{}")
    try:
        return _json.loads(raw)
    except Exception:
        return {}


def cf_manager_prefixes() -> tuple:
    """Comma-separated claim-value prefixes that mean "head of department" → CRM role manager.

    Any department/functional_role value starting with one of these prefixes maps
    to manager regardless of CF_ROLE_MAP (head-of-* combos aren't enumerable —
    e.g. "truong-phong-tai-chinh", "truong-phong-hanh-chinh", one per department).
    Example env: CF_MANAGER_PREFIXES=truong-phong-,head-of-
    """
    raw = os.environ.get("CF_MANAGER_PREFIXES", "truong-phong-,head-of-")
    return tuple(p.strip() for p in raw.split(",") if p.strip())


def cf_admin_emails() -> set:
    """Comma-separated emails that bootstrap as role=admin on FIRST login only.

    Existing users are never auto-elevated — change role via Settings UI.
    """
    raw = os.environ.get("CRM_ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}

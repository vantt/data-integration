"""Hug settings — env-driven, no domain logic.

Env vars:
  CRM_DATA_DIR     — directory holding SQLite files (default: ./data). hug.db
                     lives here alongside crm.db / cache.db.
  HUG_DB           — explicit hug.db path (default: {CRM_DATA_DIR}/hug.db)
  HUG_DOMAIN       — public scan domain baked into printed QR codes
                     (default: hug.fjp.vn) — URL is https://{HUG_DOMAIN}/h/{token}
                     (path is /h/ to match the Worker read route GET /h/:token)
  HUG_WORKER_URL   — base URL of the deployed Cloudflare Worker. When UNSET the
                     D1 push is SKIPPED (logged "pending deploy"); everything
                     else works locally. Set after the Worker (M2) is deployed.
  HUG_ADMIN_SECRET — shared secret for the HMAC X-Hug-Signature header on the
                     admin upsert route. Required only when HUG_WORKER_URL is set.
  SAPO_API_URL     — base URL for Sapo REST API (e.g. https://fwg.mysapogo.com).
                     When unset, the Sapo order validator soft-fails (amber).
  SAPO_API_KEY     — Sapo REST API key for Authorization: Bearer.
                     When unset, the Sapo order validator soft-fails (amber).
                     NOTE: as of 2026-06-23 Sapo only supports cookie-based auth
                     (Playwright SharedCookieManager); these vars are reserved for
                     future use if a REST key becomes available.
"""
from __future__ import annotations

import os


def _data_dir() -> str:
    return os.environ.get("CRM_DATA_DIR", "./data")


def hug_db_path() -> str:
    """Path to the Python-owned Hug master SQLite database."""
    default = os.path.join(_data_dir(), "hug.db")
    return os.environ.get("HUG_DB", default)


def hug_domain() -> str:
    """Public scan domain printed into QR codes (no scheme)."""
    return os.environ.get("HUG_DOMAIN", "hug.fjp.vn")


def scan_url(token: str) -> str:
    """Full public scan URL encoded into a token's QR code.

    Path is /h/{token} to match the Worker read route (GET /h/:token).
    """
    return f"https://{hug_domain()}/h/{token}"


def worker_url() -> str:
    """Base URL of the deployed Worker. Empty string => D1 push disabled."""
    return os.environ.get("HUG_WORKER_URL", "").rstrip("/")


def admin_secret() -> str:
    """Shared secret for the HMAC-signed admin upsert push."""
    return os.environ.get("HUG_ADMIN_SECRET", "")


def push_enabled() -> bool:
    """True only when the Worker URL is configured (post-M2-deploy)."""
    return bool(worker_url())


def sapo_api_url() -> str:
    """Base URL for Sapo REST API (no trailing slash). Empty when unconfigured."""
    return os.environ.get("SAPO_API_URL", "").rstrip("/")


def sapo_api_key() -> str:
    """Sapo REST API key for Authorization: Bearer. Empty when unconfigured."""
    return os.environ.get("SAPO_API_KEY", "")

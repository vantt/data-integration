"""hug.sapo_order_proxy — hybrid order-code existence check.

Strategy (decided 2026-06-23, see plan.md "Order-code validation strategy"):
  Tier 1 (instant, no auth): look up order_code in cache.db wh_order_hdr.
          Found → valid (green).  The cache is populated by the ingestion pipeline
          on each sync cycle (typically every few minutes).
  Tier 2 (live Sapo REST): NOT IMPLEMENTED — skipped.
          Reason: Sapo authenticates via Playwright cookie login (SharedCookieManager),
          not a REST API key.  The cookie store lives in ingestion/.cookies/ which is
          NOT mounted into the crm container and depends on playwright/requests packages
          absent from the crm venv.  Re-using the cookie store cross-container would
          require a shared volume mount + playwright in crm — YAGNI for now.
  Miss / cache absent / any error → amber "không kiểm tra được", NEVER hard-blocks.

The Sapo env-var path (SAPO_API_URL + SAPO_API_KEY) is retained in config.py so
it can be activated later if Sapo ever exposes a REST key, without touching this file.
"""
from __future__ import annotations

import logging
import os
import sqlite3

log = logging.getLogger(__name__)

# wh_order_hdr.order_code column confirmed via crm/sync/duckdb_reader.py:141
_CACHE_QUERY = "SELECT 1 FROM wh_order_hdr WHERE order_code = ? LIMIT 1"


def _cache_db_path() -> str:
    """Resolve cache.db path — reads CRM_CACHE_DB env var (same pattern as customer_push.py)."""
    default_dir = os.environ.get("CRM_DATA_DIR", "./data")
    return os.environ.get("CRM_CACHE_DB", os.path.join(default_dir, "cache.db"))


def check_order_exists(order_code: str, *, cache_db: str | None = None) -> dict:
    """Return a validation result for *order_code*.

    Args:
        order_code: The order code string to look up (e.g. "SO1234").
        cache_db:   Override the cache.db path (for testing).

    Returns dict with keys:
        ok:      True = valid/green, False = invalid/red, None = unknown/amber
        source:  "cache" | "none" — where the result came from
        message: Human-readable Vietnamese string for the kiosk UI
    """
    if not order_code or not order_code.strip():
        return {"ok": False, "source": "none", "message": "Mã đơn trống"}

    db_path = cache_db or _cache_db_path()

    # Tier 1: cache.db lookup (read-only — never write to serving DBs; see MEMORY feedback_duckdb_always_readonly.md)
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute(_CACHE_QUERY, (order_code.strip(),)).fetchone()
        finally:
            conn.close()

        if row is not None:
            return {"ok": True, "source": "cache", "message": "Đơn hợp lệ"}

        # Not found in cache → amber (may be a brand-new order not yet replicated)
        log.info("sapo_order_proxy: order_code=%s not in cache.db — returning amber", order_code)
        return {
            "ok": None,
            "source": "cache",
            "message": "Không tìm thấy trong cache — đơn mới hoặc chưa đồng bộ",
        }

    except sqlite3.OperationalError as exc:
        # cache.db absent (e.g. first-boot, test env without sync) → amber, not a hard failure
        log.warning("sapo_order_proxy: cache.db unavailable (%s) — returning amber", exc)
        return {
            "ok": None,
            "source": "none",
            "message": "Không kiểm tra được (cache chưa sẵn sàng)",
        }
    except Exception as exc:  # noqa: BLE001
        log.error("sapo_order_proxy: unexpected error checking order_code=%s: %s", order_code, exc)
        return {
            "ok": None,
            "source": "none",
            "message": "Không kiểm tra được (lỗi nội bộ)",
        }

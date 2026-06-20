"""customer_push.py — nightly push of the hug_customer replica to the Cloudflare Worker.

The edge needs a fresh copy of customer segmentation so its routing rules can
match on tier/recency/value_group/is_contactable without calling home (local CRM
is not reachable from the internet at scan time).

Data sources (both opened READ-ONLY — no warehouse write-back):
  cache.db   wh_customer_tier   — warehouse-derived segmentation (~7.5k rows)
  crm.db     crm_identity_link  — Hug-captured phone opt-ins (Option A overlay)

Contactability merge rule (Option A — CRM overlay, no warehouse write-back):
  is_contactable = warehouse_is_contactable
                   OR crm has a 'linked' identity_link row for this customer_id
                      with a non-null scanner_phone.

This means a masked repeat buyer who scanned their own token and left a phone
shows is_contactable=1 on the edge immediately — without waiting for the
warehouse ETL cycle to propagate the contact back through Sapo dim_customers.

Config-gating: if HUG_WORKER_URL is unset the push is skipped with a clear
"pending deploy" log.  Everything else (cache reads, CRM reads) still runs so
callers can verify data health without a live Worker.

Edge contract  POST /hug/customer/upsert
  body  {"rows": [{"customer_id": str, "tier": str,
                   "recency_days": int, "value_group": str,
                   "is_contactable": 0|1}]}
  auth  X-Hug-Signature: sha256=<hmac(HUG_ADMIN_SECRET, raw_body)>
        User-Agent: FineJapan-Hug-Push/1.0
"""
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any

from hug.config import admin_secret, push_enabled, worker_url
from hug.d1_transport import post_signed

log = logging.getLogger(__name__)

_UPSERT_PATH = "/hug/customer/upsert"
# Worker accepts up to 1 000 rows per call; ~7.5k customers → 8 batches.
_BATCH_SIZE = 500


def _crm_db_path() -> str:
    """Path to crm.db — mirrors crm/src/config.py without importing it here."""
    data_dir = os.environ.get("CRM_DATA_DIR", "./data")
    return os.path.join(data_dir, "crm.db")


def _cache_db_path() -> str:
    """Path to cache.db — mirrors crm/sync/config.py without importing it here."""
    default_dir = os.environ.get("CRM_DATA_DIR", "./data")
    return os.environ.get("CRM_CACHE_DB", os.path.join(default_dir, "cache.db"))


def _load_crm_contactable_ids(crm_db: str) -> set[str]:
    """Return the set of customer_ids that Hug has captured a phone for.

    Join key: crm_identity_link.resolved_customer_id = wh_customer_tier.customer_id
    (both are Sapo integer customer_ids stored as TEXT/INTEGER).

    Criteria: status='linked' AND scanner_phone IS NOT NULL AND
              resolved_customer_id IS NOT NULL.
    A 'needs_review' row is excluded — not yet confirmed.
    """
    if not os.path.exists(crm_db):
        log.warning("customer_push: crm.db not found at %s — CRM overlay skipped", crm_db)
        return set()

    conn = sqlite3.connect(f"file:{crm_db}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            """
            SELECT DISTINCT resolved_customer_id
            FROM   crm_identity_link
            WHERE  status = 'linked'
              AND  scanner_phone IS NOT NULL
              AND  resolved_customer_id IS NOT NULL
            """
        )
        return {str(row[0]) for row in cur.fetchall()}
    except sqlite3.OperationalError as exc:
        # Table may not exist yet (migration 0022 not yet applied on this instance).
        log.warning("customer_push: could not query crm_identity_link (%s) — overlay skipped", exc)
        return set()
    finally:
        conn.close()


def _load_tier_rows(cache_db: str) -> list[dict[str, Any]]:
    """Read all rows from wh_customer_tier in cache.db (read-only)."""
    conn = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT customer_id,
                   strategic_tier,
                   recency_days,
                   value_group,
                   is_contactable
            FROM   wh_customer_tier
            WHERE  customer_id IS NOT NULL
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _build_edge_rows(
    tier_rows: list[dict[str, Any]],
    crm_contactable: set[str],
) -> list[dict[str, Any]]:
    """Compose edge rows, merging CRM contactability overlay.

    strategic_tier → "tier" (field name in the edge contract).
    is_contactable: warehouse value OR CRM has a captured phone for this customer.
    customer_id cast to str (edge stores as TEXT).
    """
    out = []
    for r in tier_rows:
        cid = str(r["customer_id"])
        wh_contactable = int(r["is_contactable"] or 0)
        crm_contactable_flag = 1 if cid in crm_contactable else 0
        out.append({
            "customer_id":   cid,
            "tier":          r["strategic_tier"] or "UNKNOWN",
            "recency_days":  int(r["recency_days"] or 0),
            "value_group":   r["value_group"] or "UNKNOWN",
            "is_contactable": 1 if (wh_contactable or crm_contactable_flag) else 0,
        })
    return out


def _push_batches(
    edge_rows: list[dict[str, Any]],
    url: str,
    secret: str,
) -> dict[str, Any]:
    """POST edge_rows in _BATCH_SIZE chunks.  Returns aggregate result."""
    total = len(edge_rows)
    ok_count = 0
    fail_count = 0

    for start in range(0, total, _BATCH_SIZE):
        batch = edge_rows[start : start + _BATCH_SIZE]
        result = post_signed(url, secret, {"rows": batch})
        if result["ok"]:
            ok_count += len(batch)
            log.debug(
                "customer_push: batch %d–%d pushed (HTTP %d)",
                start, start + len(batch) - 1, result.get("status"),
            )
        else:
            fail_count += len(batch)
            log.error(
                "customer_push: batch %d–%d FAILED — %s",
                start, start + len(batch) - 1, result.get("error"),
            )

    log.info(
        "customer_push: %d/%d rows pushed ok, %d failed",
        ok_count, total, fail_count,
    )
    return {"total": total, "ok": ok_count, "failed": fail_count}


def run(
    cache_db: str | None = None,
    crm_db: str | None = None,
) -> dict[str, Any]:
    """Execute the nightly hug_customer push.

    Parameters allow injecting paths for tests; production uses env defaults.
    Returns a summary dict; never raises (errors are logged and reflected in
    the summary).
    """
    cache_path = cache_db or _cache_db_path()
    crm_path   = crm_db  or _crm_db_path()

    if not push_enabled():
        log.info(
            "customer_push: HUG_WORKER_URL unset — skipping push (pending deploy); "
            "cache=%s crm=%s", cache_path, crm_path,
        )
        return {"skipped": True, "reason": "pending deploy"}

    secret = admin_secret()
    if not secret:
        log.warning(
            "customer_push: HUG_WORKER_URL set but HUG_ADMIN_SECRET empty — "
            "cannot sign; skipping"
        )
        return {"skipped": True, "reason": "missing admin secret"}

    if not os.path.exists(cache_path):
        log.error("customer_push: cache.db not found at %s — aborting", cache_path)
        return {"skipped": False, "error": f"cache.db not found: {cache_path}"}

    log.info("customer_push: loading tier data from %s", cache_path)
    tier_rows = _load_tier_rows(cache_path)
    if not tier_rows:
        log.warning("customer_push: wh_customer_tier is empty — nothing to push")
        return {"skipped": False, "total": 0, "ok": 0, "failed": 0}

    log.info("customer_push: loading CRM contactability overlay from %s", crm_path)
    crm_contactable = _load_crm_contactable_ids(crm_path)
    log.info(
        "customer_push: %d tier rows, %d CRM-contactable ids",
        len(tier_rows), len(crm_contactable),
    )

    edge_rows = _build_edge_rows(tier_rows, crm_contactable)
    url = worker_url() + _UPSERT_PATH
    result = _push_batches(edge_rows, url, secret)
    return {"skipped": False, **result}

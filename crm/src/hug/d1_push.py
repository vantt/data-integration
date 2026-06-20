"""Config-gated one-way push of a bound token to the Cloudflare Worker (D1).

This is the ONLY part that depends on the deployed Worker (M2). It is gated by
HUG_WORKER_URL: when unset, push_bound_token() returns a "skipped" result and
logs "pending deploy" — so the claim station works fully offline today and
starts publishing automatically once the Worker URL + secret are configured.

Auth mirrors the existing Sapo webhook admin pattern:
  X-Hug-Signature: sha256=<hex(hmac_sha256(HUG_ADMIN_SECRET, raw_body))>

Uses only the stdlib (urllib) — no new runtime dependency.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

from hug.config import admin_secret, push_enabled, worker_url
from hug.d1_transport import post_signed, sign as _sign_fn

log = logging.getLogger(__name__)

_UPSERT_PATH = "/hug/token/upsert"


def _sign(secret: str, raw_body: bytes) -> str:
    """Thin wrapper kept for backwards-compat with tests that call d1_push._sign."""
    return _sign_fn(secret, raw_body)


def _row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
    """Project a bound hug_token row to the D1 edge row.

    Field set matches the Worker's HugTokenRow contract exactly (token,
    customer_id, op_type, order_code, channel, ship_date, sku, campaign_hint,
    status, batch_id). ``is_gift`` is intentionally NOT pushed — it is a
    local-only attribute that feeds the identity bridge (scanner != buyer), not
    edge routing, and the D1 hug_token table has no such column.

    customer_id may still be null at bind time (resolved async by the pipeline);
    the row is re-pushed on later refresh once resolved.
    """
    return {
        "token": row["token"],
        "customer_id": row["customer_id"],
        "op_type": row["op_type"],
        "order_code": row["order_code"],
        "channel": row["channel"],
        "ship_date": row["ship_date"],
        "sku": row["sku"],
        "campaign_hint": row["campaign_hint"],
        "status": row["status"],
        "batch_id": row["batch_id"],
    }


def push_bound_token(row: sqlite3.Row) -> dict[str, Any]:
    """Push one bound token to the Worker admin upsert route.

    Returns a result dict: {"ok": bool, "skipped": bool, "status"/"error": ...}.
    Never raises — the claim has already succeeded locally; the push is a
    best-effort background publish that is safe to retry later.
    """
    if not push_enabled():
        log.info("hug d1 push: HUG_WORKER_URL unset — skipping (pending deploy) token=%s", row["token"])
        return {"ok": False, "skipped": True, "reason": "pending deploy"}

    secret = admin_secret()
    if not secret:
        log.warning("hug d1 push: HUG_WORKER_URL set but HUG_ADMIN_SECRET empty — cannot sign; skipping")
        return {"ok": False, "skipped": True, "reason": "missing admin secret"}

    url = worker_url() + _UPSERT_PATH
    # Worker contract: POST /hug/token/upsert  body = { "rows": HugTokenRow[] }.
    # We push one bound token per claim; chunked batches are a later optimisation.
    envelope = {"rows": [_row_to_payload(row)]}
    result = post_signed(url, secret, envelope)
    if result["ok"]:
        log.info("hug d1 push: token=%s upserted (HTTP %d)", row["token"], result.get("status"))
        return {"ok": True, "skipped": False, "status": result["status"]}
    return {"ok": False, "skipped": False, "error": result.get("error", "unknown")}

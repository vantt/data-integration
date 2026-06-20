"""campaign_push.py — push locally-authored Hug campaigns to the Cloudflare Worker.

The edge D1 table (hug_campaign) is populated from here after every admin save.
One-way flow: CRM is the authoring source; the Worker is the runtime consumer.

Config-gating mirrors customer_push.py exactly:
  HUG_WORKER_URL unset → skip + log "pending deploy", never crash.
  HUG_ADMIN_SECRET empty when URL is set → warning + skip, never crash.

Edge contract  POST /hug/campaign/upsert
  body  {"rows": [HugCampaign, ...]}
  auth  X-Hug-Signature: sha256=<hmac(HUG_ADMIN_SECRET, raw_body)>
        User-Agent: FineJapan-Hug-Push/1.0  (Cloudflare Bot Fight Mode bypass)

quota_used is deliberately OMITTED from every push row.
The edge upsert SQL preserves the live counter:
    CASE WHEN excluded.quota_used IS NOT NULL
         THEN excluded.quota_used ELSE hug_campaign.quota_used END
Sending NULL/absent quota_used keeps the counter intact; sending a value
(even 0) would reset it. The CRM never stores quota_used — that counter
is entirely edge-owned at runtime.

targeting is stored in crm.db as a JSON STRING (TEXT column) but the edge
contract expects a JSON OBJECT. _to_edge_row() parses it before sending.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from hug.campaign_repository import list_campaigns
from hug.config import admin_secret, push_enabled, worker_url
from hug.d1_transport import post_signed

log = logging.getLogger(__name__)

_UPSERT_PATH = "/hug/campaign/upsert"


def _to_edge_row(row: dict) -> dict:
    """Project a crm_hug_campaign dict to the Worker HugCampaign contract.

    Key behaviours:
    - targeting: stored as a JSON STRING in crm.db; sent as a JSON OBJECT to
      the edge (the Worker validates it as an object, not a string).
    - quota_used: intentionally absent. The edge upsert preserves the live
      counter when quota_used is NULL/absent — omitting it is the only safe
      way to avoid resetting a campaign's runtime counter on every CRM edit.
    """
    # Parse targeting from JSON string to object; fall back to empty object.
    raw_targeting = row.get("targeting") or "{}"
    try:
        targeting_obj: Any = json.loads(raw_targeting)
    except (json.JSONDecodeError, TypeError):
        log.warning(
            "campaign_push: campaign %r has invalid targeting JSON %r — using {}",
            row.get("campaign_id"), raw_targeting,
        )
        targeting_obj = {}

    return {
        "campaign_id":      row["campaign_id"],
        "name":             row["name"],
        "targeting":        targeting_obj,   # object, not string
        "destination_type": row["destination_type"],
        "destination_url":  row["destination_url"],
        "offer_ref":        row.get("offer_ref"),
        "priority":         row["priority"],
        "schedule_start":   row.get("schedule_start"),
        "schedule_end":     row.get("schedule_end"),
        "quota_total":      row.get("quota_total"),
        # quota_used intentionally omitted — edge-owned runtime counter.
        # See module docstring for the CASE-WHEN preservation logic.
        "status":           row["status"],
        "updated_at":       row.get("updated_at"),
    }


def push_campaign(row: dict) -> dict:
    """Push one campaign row to the Worker after an admin save.

    Args:
        row: A dict representing a crm_hug_campaign row (as returned by
             campaign_repository.upsert_campaign or get_campaign).

    Returns:
        {"ok": True, "skipped": False}                   — success
        {"ok": False, "skipped": True,  "reason": str}  — config-gated skip
        {"ok": False, "skipped": False, "error": str}   — HTTP/network failure

    Never raises — caller is fire-and-forget (local row already committed).
    """
    if not push_enabled():
        log.info(
            "campaign_push: HUG_WORKER_URL unset — skipping push for %r (pending deploy)",
            row.get("campaign_id"),
        )
        return {"ok": False, "skipped": True, "reason": "pending deploy"}

    secret = admin_secret()
    if not secret:
        log.warning(
            "campaign_push: HUG_WORKER_URL set but HUG_ADMIN_SECRET empty — "
            "cannot sign; skipping push for %r",
            row.get("campaign_id"),
        )
        return {"ok": False, "skipped": True, "reason": "missing admin secret"}

    edge_row = _to_edge_row(row)
    url = worker_url() + _UPSERT_PATH
    result = post_signed(url, secret, {"rows": [edge_row]})

    if result["ok"]:
        log.info(
            "campaign_push: pushed %r (HTTP %d)",
            row.get("campaign_id"), result.get("status"),
        )
        return {"ok": True, "skipped": False}
    else:
        log.error(
            "campaign_push: push failed for %r — %s",
            row.get("campaign_id"), result.get("error"),
        )
        return {"ok": False, "skipped": False, "error": result.get("error")}


def push_all_campaigns(conn: sqlite3.Connection) -> dict:
    """Reconcile push: send all non-archived campaigns to the Worker in one batch.

    Used for initial sync after a Worker deploy, or manual recovery.
    Campaign count is expected to stay under 100; no chunking needed now.
    Add batching here if campaign count grows beyond a few hundred.

    Args:
        conn: Open sqlite3 connection to crm.db (caller controls lifecycle).

    Returns:
        {"ok": False, "skipped": True, "reason": str}    — config-gated skip
        {"ok": True,  "skipped": False, "total": int}    — success
        {"ok": False, "skipped": False, "error": str,
         "total": int}                                    — HTTP/network failure

    Never raises.
    """
    if not push_enabled():
        log.info(
            "campaign_push: HUG_WORKER_URL unset — skipping reconcile push (pending deploy)"
        )
        return {"ok": False, "skipped": True, "reason": "pending deploy"}

    secret = admin_secret()
    if not secret:
        log.warning(
            "campaign_push: HUG_WORKER_URL set but HUG_ADMIN_SECRET empty — "
            "cannot sign; skipping reconcile push"
        )
        return {"ok": False, "skipped": True, "reason": "missing admin secret"}

    # Fetch all non-archived campaigns (active + paused) sorted by priority.
    all_rows = list_campaigns(conn)
    active_rows = [dict(r) for r in all_rows if r["status"] != "archived"]

    if not active_rows:
        log.info("campaign_push: no non-archived campaigns to push")
        return {"ok": True, "skipped": False, "total": 0}

    edge_rows = [_to_edge_row(r) for r in active_rows]
    url = worker_url() + _UPSERT_PATH
    result = post_signed(url, secret, {"rows": edge_rows})

    total = len(edge_rows)
    if result["ok"]:
        log.info(
            "campaign_push: reconcile push sent %d campaigns (HTTP %d)",
            total, result.get("status"),
        )
        return {"ok": True, "skipped": False, "total": total}
    else:
        log.error(
            "campaign_push: reconcile push failed for %d campaigns — %s",
            total, result.get("error"),
        )
        return {"ok": False, "skipped": False, "error": result.get("error"), "total": total}

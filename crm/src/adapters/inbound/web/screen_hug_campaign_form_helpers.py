"""screen_hug_campaign_form_helpers.py — form parsing helpers for campaign admin.

No FastAPI import — independently testable alongside the _html helpers.

Exported:
  parse_targeting(form_multi)          -> targeting dict from multi-value form data
  build_campaign_row(cid, form, tgt)   -> full campaign dict ready for upsert_campaign()
  form_to_partial(form_multi)          -> partial campaign dict for form re-render on error
  safe_campaign_id(raw)                -> validated slug or None
  attempt_push(saved_row)              -> push_campaign best-effort; returns bool
  VALID_STATUS_ACTIONS                 -> frozenset of accepted action names
  STATUS_FOR_ACTION                    -> {action: new_status} mapping
"""
from __future__ import annotations

import json
import logging
import re

from hug.targeting_catalog import TARGETING_CATALOG
from hug.campaign_push import push_campaign

log = logging.getLogger(__name__)

# campaign_id: alphanumeric, hyphen, underscore only (mirrors repository constraint).
_SAFE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

VALID_STATUS_ACTIONS: frozenset[str] = frozenset({"pause", "activate", "archive"})
STATUS_FOR_ACTION: dict[str, str] = {
    "pause": "paused",
    "activate": "active",
    "archive": "archived",
}


def safe_campaign_id(raw: str) -> str | None:
    """Return the campaign_id if it matches the safe slug pattern, else None."""
    cid = raw.strip()
    return cid if _SAFE_ID_RE.match(cid) else None


def parse_targeting(form_multi: dict[str, list[str]]) -> dict:
    """Assemble a targeting dict from multi-value form fields.

    Field naming:
      val_<attr>   — checkbox values for list-type attrs (0..N checked)
      gte_<attr>   — lower bound for range attrs (empty string = omit)
      lte_<attr>   — upper bound for range attrs (empty string = omit)

    Rules:
    - list attr with no checked boxes → absent from targeting (no filter applied).
    - range attr with neither bound → absent from targeting.
    - is_contactable values arrive as strings "0"/"1"; kept as strings
      because the edge Worker uses String() coercion.
    """
    targeting: dict = {}
    for attr, spec in TARGETING_CATALOG.items():
        if spec["type"] == "list":
            vals = form_multi.get(f"val_{attr}", [])
            if vals:
                targeting[attr] = vals
        elif spec["type"] == "range":
            gte_raw = (form_multi.get(f"gte_{attr}", [""])[0] or "").strip()
            lte_raw = (form_multi.get(f"lte_{attr}", [""])[0] or "").strip()
            rule: dict = {}
            if gte_raw:
                try:
                    rule["gte"] = float(gte_raw) if "." in gte_raw else int(gte_raw)
                except ValueError:
                    pass
            if lte_raw:
                try:
                    rule["lte"] = float(lte_raw) if "." in lte_raw else int(lte_raw)
                except ValueError:
                    pass
            if rule:
                targeting[attr] = rule
    return targeting


def build_campaign_row(
    campaign_id: str,
    form_multi: dict[str, list[str]],
    targeting: dict,
) -> dict:
    """Build a complete campaign dict ready for upsert_campaign()."""
    def first(key: str, default: str = "") -> str:
        return (form_multi.get(key, [default])[0] or "").strip()

    priority_raw = first("priority", "100")
    try:
        priority = int(priority_raw)
    except ValueError:
        priority = 100

    quota_raw = first("quota_total", "")
    quota_total = None
    if quota_raw:
        try:
            quota_total = int(quota_raw)
        except ValueError:
            quota_total = None

    return {
        "campaign_id": campaign_id,
        "name": first("name"),
        "destination_type": first("destination_type", "zalo_oa"),
        "destination_url": first("destination_url"),
        "offer_ref": first("offer_ref") or None,
        "priority": priority,
        "schedule_start": first("schedule_start") or None,
        "schedule_end": first("schedule_end") or None,
        "quota_total": quota_total,
        "status": first("status", "active"),
        "targeting": json.dumps(targeting, ensure_ascii=False),
    }


def form_to_partial(form_multi: dict[str, list[str]]) -> dict:
    """Reconstruct a partial campaign dict from form fields for form re-render on error."""
    def first(key: str, default: str = "") -> str:
        return (form_multi.get(key, [default])[0] or "").strip()

    return {
        "campaign_id": first("campaign_id"),
        "name": first("name"),
        "destination_type": first("destination_type", "zalo_oa"),
        "destination_url": first("destination_url"),
        "offer_ref": first("offer_ref") or None,
        "priority": first("priority", "100") or "100",
        "quota_total": first("quota_total") or None,
        "schedule_start": first("schedule_start") or None,
        "schedule_end": first("schedule_end") or None,
        "status": first("status", "active"),
        # targeting re-rendered from live form fields in the HTML helper; placeholder only.
        "targeting": "{}",
    }


def attempt_push(saved_row: dict) -> bool:
    """Push a saved campaign row to the edge Worker. Returns True on success or skip."""
    result = push_campaign(saved_row)
    return result.get("ok", False) or result.get("skipped", False)


def priority_duplicate_warning(port, priority: int, own_id: str) -> str:
    """Return a warning string if another non-archived campaign shares this priority.

    Soft enforcement: the caller decides whether to append to flash. own_id is
    excluded so an edit-save does not warn against itself.

    Kept FastAPI-free (no HTTP imports) so it is directly testable without Docker.
    port must implement HugCampaignPort (list_campaigns() and suggest_next_priority()).
    """
    import html as _html

    others = [
        c for c in port.list_campaigns()
        if c["priority"] == priority
        and c["campaign_id"] != own_id
        and c["status"] != "archived"
    ]
    if not others:
        return ""
    other = others[0]
    next_free = port.suggest_next_priority()
    return (
        f" ⚠️ Priority {priority} cũng dùng bởi "
        f"'{_html.escape(str(other['name']))}' — tie-break theo campaign_id. "
        f"Gợi ý priority tiếp theo: {next_free}."
    )

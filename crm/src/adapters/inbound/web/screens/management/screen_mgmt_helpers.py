"""Shared helpers for the management screen sub-routers.

Used by screen_mgmt_segments / screen_mgmt_campaigns / screen_mgmt_dedup /
screen_mgmt_settings. Keeps validation, JSON rule building, and party-name
lookup logic in one place so the route modules stay focused on HTTP handling.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _is_valid_hex_color(color: str) -> bool:
    return color == "" or bool(_HEX_RE.match(color))


def _build_rule_definition(
    value_group: list[str],
    customer_status: str,
    days_since: str,
    channel: str,
) -> str:
    rule: dict[str, Any] = {}
    if value_group:
        rule["value_group"] = value_group
    if customer_status.strip():
        rule["customer_status"] = customer_status.strip()
    if days_since.strip():
        try:
            n = int(days_since.strip())
            if n > 0:
                rule["days_since_last_order_gte"] = n
        except ValueError:
            pass
    if channel.strip():
        rule["channel_preference"] = channel.strip()
    return json.dumps(rule) if rule else ""


def _parse_options(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _safe(fn, default, label: str):
    try:
        return fn()
    except Exception:
        if label:
            logger.exception("%s", label)
        return default


def _build_party_names(parties_svc: Any, targets: list) -> dict[str, str]:
    out: dict[str, str] = {}
    for t in targets:
        if t.party_id in out:
            continue
        # Default-capture pid to avoid late-binding if lambdas are ever deferred.
        p = _safe(lambda pid=t.party_id: parties_svc.get_by_id(pid), None, "")
        if p:
            out[t.party_id] = p.display_name
    return out


def _build_dedup_party_names(parties_svc: Any, candidates: list) -> dict[str, str]:
    seen: set[str] = set()
    out: dict[str, str] = {}
    for c in candidates:
        for pid in (c.party_a, c.party_b):
            if pid in seen:
                continue
            seen.add(pid)
            # Default-capture pid to avoid late-binding if lambdas are ever deferred.
            p = _safe(lambda pid=pid: parties_svc.get_by_id(pid), None, "")
            if p:
                out[pid] = p.display_name
    return out

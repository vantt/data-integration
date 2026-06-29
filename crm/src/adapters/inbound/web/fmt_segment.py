"""Segment rule-definition helpers for the CRM web adapter.

Extract individual rule values from a segment's JSON definition for template display.
All functions are pure — safe to call from Jinja2 filters.
"""
from __future__ import annotations

import json

__all__ = ["segment_channel_pref", "segment_days_since"]


def _segment_rule(segment: object, key: str) -> str:
    """Return string value of `key` from a segment's JSON definition, or '' on any failure."""
    if segment is None:
        return ""
    defn = getattr(segment, "definition", "") or ""
    try:
        data = json.loads(defn)
        return str(data.get(key, ""))
    except Exception:
        return ""


def segment_channel_pref(segment: object) -> str:
    """Extract channel_preference value from a segment's rule definition for template display."""
    return _segment_rule(segment, "channel_preference")


def segment_days_since(segment: object) -> str:
    """Extract recency_days value from a segment's rule definition for template display."""
    return _segment_rule(segment, "recency_days")

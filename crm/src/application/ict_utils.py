"""ICT (Asia/Ho_Chi_Minh, UTC+7) time utilities for the CRM server."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

_ICT = timezone(timedelta(hours=7))


def ict_local_to_utc(ict_str: str) -> str:
    """Parse a datetime-local HTML input (assumed ICT/UTC+7) and return UTC ISO-8601.

    Input format: '2026-06-29T14:30' (no timezone, assumed ICT).
    Output format: '2026-06-29T07:30:00.000Z' (UTC with milliseconds).
    Returns empty string on parse failure.
    """
    try:
        dt = datetime.strptime(ict_str.strip(), "%Y-%m-%dT%H:%M").replace(tzinfo=_ICT)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception:
        return ""

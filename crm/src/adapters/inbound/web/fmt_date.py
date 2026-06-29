"""Date/time formatting helpers for the CRM web adapter.

Parses UTC ISO-8601 strings, displays in ICT (Asia/Ho_Chi_Minh).
All functions are pure — safe to call from Jinja2 filters.
"""
from __future__ import annotations

import zoneinfo
from datetime import datetime, timezone

__all__ = [
    "format_date_ict", "format_datetime_ict", "format_relative",
    "recency_days_label", "fmt_date_key", "days_since", "format_ict",
]

_ICT = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")
_UTC = timezone.utc

_RELATIVE_THRESHOLDS = [
    (60, "giây", 1),
    (3600, "phút", 60),
    (86400, "giờ", 3600),
    (86400 * 30, "ngày", 86400),
    (86400 * 365, "tháng", 86400 * 30),
    (None, "năm", 86400 * 365),
]


def _parse_iso(iso_str: str | None) -> datetime | None:
    """Parse UTC ISO-8601 string into an aware datetime. Returns None on failure."""
    if not iso_str:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(iso_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_UTC)
            return dt
        except ValueError:
            continue
    return None


def format_date_ict(iso_str: str | None) -> str:
    """Parse UTC ISO-8601 date string, return 'DD/MM/YYYY' in ICT."""
    if not iso_str:
        return "—"
    dt = _parse_iso(iso_str)
    if dt is None:
        return iso_str
    local = dt.astimezone(_ICT)
    return local.strftime("%d/%m/%Y")


def format_datetime_ict(iso_str: str | None) -> str:
    """Parse UTC ISO-8601 datetime string, return 'DD/MM/YYYY HH:MM ICT'."""
    if not iso_str:
        return "—"
    dt = _parse_iso(iso_str)
    if dt is None:
        return iso_str
    local = dt.astimezone(_ICT)
    # Date-only inputs (no T) → date only, no time suffix
    if "T" not in iso_str and not iso_str.endswith("Z"):
        return local.strftime("%d/%m/%Y")
    return local.strftime("%d/%m/%Y %H:%M ICT")


def format_relative(iso_str: str | None) -> str:
    """Return a Vietnamese relative time string (e.g. '2 giờ trước').

    Parses a UTC ISO-8601 string; compares to now(UTC).
    """
    if not iso_str:
        return "—"
    dt = _parse_iso(iso_str)
    if dt is None:
        return iso_str
    delta = int((datetime.now(_UTC) - dt).total_seconds())
    if delta < 0:
        return "vừa xong"
    if delta < 5:
        return "vừa xong"
    for limit, unit, divisor in _RELATIVE_THRESHOLDS:
        if limit is None or delta < limit:
            n = delta // divisor
            return f"{n} {unit} trước"
    return "—"  # unreachable


def recency_days_label(date_key: int | None) -> str:
    """Return 'N d' (days since a YYYYMMDD date_key) for the Recency KPI. Returns '—' for None/0."""
    if not date_key:
        return "—"
    try:
        s = str(int(date_key))
        if len(s) == 8:
            dt = datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]), tzinfo=_UTC)
            days = (datetime.now(_UTC) - dt).days
            return f"{max(0, days)} d"
    except (TypeError, ValueError):
        pass
    return "—"


def fmt_date_key(date_key: int | None) -> str:
    """Convert YYYYMMDD integer date_key to 'dd/mm/yyyy'. Returns '—' for falsy values."""
    if not date_key:
        return "—"
    try:
        s = str(int(date_key))
        if len(s) == 8:
            return f"{s[6:8]}/{s[4:6]}/{s[0:4]}"
    except (TypeError, ValueError):
        pass
    return "—"


def days_since(date_str: str | None) -> str:
    """Return compact tenure string, e.g. '626 d (1.7 y)'."""
    if not date_str:
        return "—"
    dt = _parse_iso(date_str)
    if dt is None:
        return "—"
    elapsed = int((datetime.now(_UTC) - dt).total_seconds())
    if elapsed < 0:
        return "—"
    total_days = elapsed // 86400
    years = total_days / 365
    if years >= 1:
        return f"{total_days} d ({years:.1f} y)"
    return f"{total_days} d"


# alias
format_ict = format_date_ict

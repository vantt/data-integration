"""Formatting helpers for the CRM web adapter.

Ported from Go:
  crm/app/internal/adapters/inbound/web/format_helpers.go
  crm/app/internal/adapters/inbound/web/templates/helpers.go

All functions are pure — no side effects, safe to call from Jinja2 filters.
"""
from __future__ import annotations

import zoneinfo
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

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


def format_vnd(amount: float | None) -> str:
    """Format a VND amount with dot-separated thousands and 'đ' suffix.

    None → '—'; 0 → '—' (matches Go formatVNDHelper behaviour).
    """
    if amount is None:
        return "—"
    try:
        int_amount = int(Decimal(str(amount)).quantize(Decimal("1")))
    except (InvalidOperation, ValueError, TypeError):
        return "—"
    if int_amount == 0:
        return "—"
    formatted = f"{abs(int_amount):,}".replace(",", ".")
    prefix = "−" if int_amount < 0 else ""
    return f"{prefix}{formatted}đ"


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


def truncate_str(s: str, n: int) -> str:
    """Truncate s to n runes, appending '…' if truncated."""
    if not s:
        return s
    runes = list(s)
    if len(runes) <= n:
        return s
    return "".join(runes[:n]) + "…"


# aliases
fmt_vnd = format_vnd
format_ict = format_date_ict


def join_nonempty(items: list, sep: str = ", ") -> str:
    """Join non-empty/non-None items with sep."""
    return sep.join(str(x) for x in items if x)


# ── Badge / CSS helpers (used as Jinja2 globals) ─────────────────────────────

_ACTION_TYPE_CSS: dict[str, str] = {
    "CALL_NOW":         "chip--danger",
    "WIN_BACK":         "chip--warning",
    "REORDER_NUDGE":    "chip--info",
    "UPSELL":           "chip--success",
    "CROSS_SELL":       "chip--success",
    "COLLECT_FEEDBACK": "chip--neutral",
}


def action_type_badge_class(action_type: str) -> str:
    return _ACTION_TYPE_CSS.get(action_type or "", "chip--neutral")


_TASK_STATUS_CSS: dict[str, str] = {
    "open":        "bdg--open",
    "in_progress": "bdg--progress",
    "done":        "bdg--done",
    "cancelled":   "bdg--cancelled",
}


def task_status_css(status: str) -> str:
    return _TASK_STATUS_CSS.get(status or "", "bdg--neutral")


_CONV_STATUS_CSS: dict[str, str] = {
    "open":     "bdg--open",
    "closed":   "bdg--done",
    "pending":  "bdg--progress",
}


def conv_status_bdg(status: str) -> str:
    return _CONV_STATUS_CSS.get(status or "", "bdg--neutral")


_CAMPAIGN_STATUS_CSS: dict[str, str] = {
    "draft":     "bdg--neutral",
    "active":    "bdg--open",
    "completed": "bdg--done",
    "paused":    "bdg--progress",
    "archived":  "bdg--cancelled",
}


def campaign_status_bdg(status: str) -> str:
    return _CAMPAIGN_STATUS_CSS.get(status or "", "bdg--neutral")


_TARGET_STATUS_CSS: dict[str, str] = {
    "pending":   "bdg--neutral",
    "sent":      "bdg--progress",
    "responded": "bdg--open",
    "converted": "bdg--done",
    "opted_out": "bdg--cancelled",
}


def target_status_bdg(status: str) -> str:
    return _TARGET_STATUS_CSS.get(status or "", "bdg--neutral")


def customer_label(name: str | None, key: str | None) -> str:
    """Return display label for a customer: name if available, else key."""
    return name or key or "—"


def segment_days_since(segment: object) -> str:
    """Extract recency_days value from a segment's rule definition for template display."""
    import json as _json
    if segment is None:
        return ""
    defn = getattr(segment, "definition", "") or ""
    try:
        data = _json.loads(defn)
        return str(data.get("recency_days", ""))
    except Exception:
        return ""

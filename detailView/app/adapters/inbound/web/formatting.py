"""Jinja2 filters and template helpers for the web adapter.

Registered on the Jinja2 environment by register_filters(env).
All formatters are pure functions — no side effects, no imports from
non-domain modules at call time.
"""
from __future__ import annotations

import zoneinfo
from datetime import datetime
from decimal import Decimal, InvalidOperation

# ICT timezone used for all timestamp display
_ICT = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")


# ---------------------------------------------------------------------------
# Filter: vnd — Money → Vietnamese Dong formatted string
# ---------------------------------------------------------------------------
def vnd(value: Decimal | float | int | None) -> str:
    """Format a monetary amount as VND with thousands separator and ₫ suffix.

    None or un-parseable → '—'  (em-dash, not a hyphen).
    Examples:
        1_250_000  →  '1.250.000 ₫'
        0          →  '0 ₫'
        None       →  '—'
    """
    if value is None:
        return "—"
    try:
        # Coerce Decimal / float / int uniformly
        amount = int(Decimal(str(value)).quantize(Decimal("1")))
    except (InvalidOperation, ValueError, TypeError):
        return "—"
    # Vietnamese convention: dot as thousands separator
    formatted = f"{amount:,}".replace(",", ".")
    return f"{formatted} ₫"


# ---------------------------------------------------------------------------
# Filter: pct — float fraction → percentage string
# ---------------------------------------------------------------------------
def pct(value: float | None, *, decimals: int = 1) -> str:
    """Format a fraction (0..1) as a percentage string.

    None → '—'
    0.304 → '30.4%'
    Negative values are shown as-is (e.g. loss margin).
    """
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return "—"


# ---------------------------------------------------------------------------
# Filter: dt — datetime → ICT 'YYYY-MM-DD HH:mm'
# ---------------------------------------------------------------------------
def dt(value: datetime | None) -> str:
    """Format a datetime (aware or naive-UTC) as ICT 'YYYY-MM-DD HH:mm'.

    Naive datetimes are assumed to be UTC per pipeline convention.
    None → '—'
    """
    if value is None:
        return "—"
    if not isinstance(value, datetime):
        return "—"
    try:
        if value.tzinfo is None:
            # Pipeline stores UTC-naive — attach UTC before converting
            value = value.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        ict_dt = value.astimezone(_ICT)
        return ict_dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"


# ---------------------------------------------------------------------------
# Filter: dateonly — datetime/date → 'YYYY-MM-DD' (ICT for datetime)
# ---------------------------------------------------------------------------
def dateonly(value) -> str:
    """Format as date string only (no time component).

    Accepts datetime or date objects. None → '—'
    """
    if value is None:
        return "—"
    try:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
            value = value.astimezone(_ICT).date()
        return value.strftime("%Y-%m-%d")
    except Exception:
        return "—"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def register_filters(env) -> None:
    """Register all custom filters onto a Jinja2 Environment instance."""
    env.filters["vnd"] = vnd
    env.filters["pct"] = pct
    env.filters["dt"] = dt
    env.filters["dateonly"] = dateonly

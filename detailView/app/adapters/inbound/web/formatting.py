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
# Global helper: comp_segments — composition bar segment list
# Returns a list of {cls, width_pct, label, amount} for OrderFinancial.
# Arithmetic done in Python; template iterates result, no inline math needed.
# Segments: COGS | Promo | Platform fees | Overhead | Net profit (or loss).
# All percentages are of net_revenue (the base). Segments that are 0/None
# are included with 0 width so the legend can still list them if desired.
# ---------------------------------------------------------------------------
def comp_segments(financial) -> list[dict]:
    """Compute composition bar segments from an OrderFinancial instance.

    Returns a list of segment dicts suitable for direct iteration in a template:
        [{cls: str, width_pct: float, label: str, amount: float}]
    Only segments with width_pct > 0 are usable for rendering (template can skip
    segments where width_pct == 0). Returns empty list when net_revenue is falsy.
    """
    try:
        net = float(financial.net_revenue or 0)
        if net <= 0:
            return []
        cogs     = float(financial.cogs_amount or 0)
        promo    = float(financial.promo_goods_cost or 0)
        fees     = float(abs(financial.shopee_platform_fees or 0))
        overhead = float(financial.allocated_overhead or 0)
        # net profit = channel_net_profit minus overhead (fully loaded)
        # Use channel_net_profit as the contribution base; overhead shown separately
        cnp      = float(financial.channel_net_profit or 0)
        fl_net   = float(financial.fully_loaded_net_profit or cnp)

        def _pct(v: float) -> float:
            p = round(v / net * 100, 1)
            return max(p, 0.0)

        segments = [
            {"cls": "comp-seg comp-seg--cogs",  "width_pct": _pct(cogs),     "label": "COGS",           "amount": cogs},
            {"cls": "comp-seg comp-seg--promo",  "width_pct": _pct(promo),    "label": "Promo goods",    "amount": promo},
            {"cls": "comp-seg comp-seg--fees",   "width_pct": _pct(fees),     "label": "Platform fees",  "amount": fees},
            {"cls": "comp-seg comp-seg--oh",     "width_pct": _pct(overhead), "label": "Overhead",       "amount": overhead},
        ]
        # Residual: fully-loaded net profit (positive → profit, negative → loss shown in cost color)
        residual = fl_net if overhead > 0 else cnp
        if residual >= 0:
            segments.append({"cls": "comp-seg comp-seg--profit", "width_pct": _pct(residual), "label": "Net profit", "amount": residual})
        else:
            # Loss: show 0-width placeholder so legend can still display
            segments.append({"cls": "comp-seg comp-seg--loss", "width_pct": 0.0, "label": "Loss", "amount": residual})

        return [s for s in segments if s["width_pct"] > 0]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def register_filters(env) -> None:
    """Register all custom filters onto a Jinja2 Environment instance."""
    env.filters["vnd"] = vnd
    env.filters["pct"] = pct
    env.filters["dt"] = dt
    env.filters["dateonly"] = dateonly
    env.globals["comp_segments"] = comp_segments

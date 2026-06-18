"""Formatting helpers for the CRM web adapter.

Ported from Go:
  crm/src/internal/adapters/inbound/web/format_helpers.go
  crm/src/internal/adapters/inbound/web/templates/helpers.go

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


# aliases
fmt_vnd = format_vnd
format_ict = format_date_ict


def join_nonempty(items: list, sep: str = ", ") -> str:
    """Join non-empty/non-None items with sep."""
    return sep.join(str(x) for x in items if x)


# ── Badge / CSS helpers (used as Jinja2 globals/filters) ─────────────────────
# All lookups delegate to badge_catalog — single source of truth for colors+hints.

from .badge_catalog import bdg_lookup, bdg_mod_cls, bdg_full_cls, bdg_hint  # noqa: E402


def action_type_badge_class(action_type: str) -> str:
    return bdg_mod_cls("action_type", action_type)


def task_status_css(status: str) -> str:
    return bdg_mod_cls("task_status", status)


def task_status_chip_class(status: str) -> str:
    return bdg_mod_cls("task_status", status)


def conv_status_bdg(status: str) -> str:
    return bdg_mod_cls("conv_status", status)


def campaign_status_bdg(status: str) -> str:
    return bdg_mod_cls("campaign_status", status)


def target_status_bdg(status: str) -> str:
    return bdg_mod_cls("campaign_target", status)


def status_badge_class(status: str) -> str:
    return bdg_mod_cls("party_status", status)


def customer_label(name: str | None, key: str | None) -> str:
    """Return display label for a customer: name if available, else key."""
    return name or key or "—"


# Jinja2 filter helpers — called as: value | bdg_cls('domain'), value | bdg_tip('domain')
def bdg_cls_filter(key: str, domain: str) -> str:
    """Full CSS class for a badge: 'bdg bdg--good' | 'bdg'."""
    return bdg_full_cls(domain, key)


def bdg_tip_filter(key: str, domain: str) -> str:
    """Vietnamese tooltip text for a domain+key."""
    return bdg_hint(domain, key)


# ── Order detail helpers ──────────────────────────────────────────────────────

def fmt_pct(value: float | None) -> str:
    """Format a 0–1 decimal fraction as a percentage string, e.g. 0.125 → '12.5%'."""
    if value is None:
        return "—"
    try:
        pct = float(value) * 100
        return f"{pct:.1f}%".rstrip("0").rstrip(".")  + "%"
    except (TypeError, ValueError):
        return "—"


def fmt_vnd_signed(amount: int | float | None) -> str:
    """VND amount with explicit +/- prefix (negatives use '−', positives use '+')."""
    if amount is None:
        return "—"
    try:
        int_amount = int(amount)
    except (TypeError, ValueError):
        return "—"
    if int_amount == 0:
        return "0đ"
    formatted = f"{abs(int_amount):,}".replace(",", ".")
    prefix = "+" if int_amount > 0 else "−"
    return f"{prefix}{formatted}đ"


# Tone filters — return CSS modifier suffix ('good'|'warn'|'bad'|'accent'|'')
# Used in templates as: bdg--{{ value | order_status_tone }}

def order_status_tone(status: str) -> str:
    return bdg_lookup("order_status", (status or "").lower()).css_mod


def payment_tone(status: str) -> str:
    return bdg_lookup("payment_status", (status or "").lower()).css_mod


def ship_tone(status: str) -> str:
    return bdg_lookup("fulfillment_status", (status or "").lower()).css_mod


def verdict_tone(financial) -> str:
    """Return 'positive', 'negative', or 'neutral' based on channel_net_profit."""
    try:
        profit = getattr(financial, "channel_net_profit", None)
        if profit is None:
            return "neutral"
        if int(profit) > 0:
            return "positive"
        if int(profit) < 0:
            return "negative"
    except (TypeError, ValueError):
        pass
    return "neutral"


_VERDICT_WORD: dict[str, str] = {
    "positive": "Có lãi",
    "negative": "Lỗ",
    "neutral":  "Hòa vốn",
}


def verdict_word(tone: str) -> str:
    return _VERDICT_WORD.get(tone or "", "—")


def segment_channel_pref(segment: object) -> str:
    """Extract channel_preference value from a segment's rule definition for template display."""
    import json as _json
    if segment is None:
        return ""
    defn = getattr(segment, "definition", "") or ""
    try:
        data = _json.loads(defn)
        return str(data.get("channel_preference", ""))
    except Exception:
        return ""


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

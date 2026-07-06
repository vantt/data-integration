"""Badge / CSS class and status-tone helpers for the CRM web adapter.

All lookups delegate to badge_catalog — single source of truth for colors+hints.
Used as Jinja2 globals/filters. All functions are pure.
"""
from __future__ import annotations

from .badge_catalog import bdg_lookup, bdg_mod_cls, bdg_full_cls, bdg_hint, bdg_label

__all__ = [
    "action_type_badge_class", "task_status_css", "task_status_chip_class",
    "conv_status_bdg", "campaign_status_bdg", "target_status_bdg",
    "status_badge_class", "customer_label", "bdg_cls_filter", "bdg_tip_filter",
    "bdg_label_filter",
    "order_status_tone", "payment_tone", "ship_tone", "verdict_tone", "verdict_word",
]


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


def bdg_label_filter(key: str, domain: str) -> str:
    """Short VN label for a domain+key — used as the primary badge TEXT."""
    return bdg_label(domain, key)


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

"""Shared Jinja2 templates factory for the web layer.

Single seam for constructing the Jinja environment so every router shares the
same configuration. Production: ``auto_reload=False`` — templates are baked
into the container image and never change at runtime, while the default
(``auto_reload=True``) makes Jinja re-stat the filesystem on every
``{% include %}``. Under the container FS that stat costs ~8 ms, so loop-heavy
pages (the worklist renders ~8.5k icon includes) take ~17 s instead of ~20 ms.

Dev: set ``CRM_DEV_RELOAD=1`` to enable ``auto_reload=True`` so template edits
are picked up on the next request without restarting the container.

A preconfigured ``jinja2.Environment`` is passed to Starlette (rather than
``**env_options``) because Starlette deprecated forwarding env options. The
environment mirrors Starlette's defaults: a filesystem loader and
``autoescape=True`` (HTML escaping — do not drop, templates rely on it).
"""
from __future__ import annotations

import os
from datetime import date

import jinja2
from fastapi.templating import Jinja2Templates


def make_templates(directory: str) -> Jinja2Templates:
    """Return a Jinja2Templates instance.

    auto_reload follows CRM_DEV_RELOAD env var (1 = dev, anything else = prod).
    """
    dev = os.environ.get("CRM_DEV_RELOAD", "0") == "1"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(directory),
        autoescape=True,
        auto_reload=dev,
    )
    # today() callable so it resolves at render time, not at startup
    env.globals["today"] = lambda: date.today().isoformat()

    # Margin quality thresholds (visual classification)
    _MARGIN_GOOD = 0.28
    _MARGIN_BAD = 0.24

    def _fmt_discount_pct(rate) -> str:
        if rate is None:
            return ""
        return f"{rate * 100:.0f}%"

    def _margin_quality_cls(pct) -> str:
        if pct is None:
            return ""
        if pct >= _MARGIN_GOOD:
            return "pct--good"
        if pct < _MARGIN_BAD:
            return "pct--bad"
        return ""

    # ── Confidence level ──────────────────────────────────────────────
    _CONF_LABEL = {"high": "cao", "medium": "vừa", "low": "thấp"}
    _CONF_TONE  = {"high": "good", "medium": "warn", "low": "bad"}
    _CONF_COLOR = {
        "high":   "var(--moss-500)",
        "medium": "var(--accent)",
        "low":    "var(--fg-tertiary)",
    }

    def _confidence_label(level) -> str:
        return _CONF_LABEL.get(level or "", level or "")

    def _confidence_tone(level) -> str:
        return _CONF_TONE.get(level or "", "warn")

    def _confidence_color(level) -> str:
        return _CONF_COLOR.get(level or "", "var(--fg-tertiary)")

    # ── Action type (mart_customer_action_queue) ──────────────────────
    _ACTION_LABEL = {
        "CALL_NOW":         "Gọi điện ngay",
        "REORDER_NUDGE":    "Nhắc tái mua",
        "WIN_BACK":         "Win-back",
        "SECOND_ORDER":     "Đơn hàng 2",
        "HIGH_CANCEL_RISK": "Rủi ro huỷ",
    }
    _ACTION_TONE = {
        "CALL_NOW":         "bad",
        "REORDER_NUDGE":    "warn",
        "WIN_BACK":         "warn",
        "SECOND_ORDER":     "good",
        "HIGH_CANCEL_RISK": "bad",
    }

    def _action_type_label(atype) -> str:
        return _ACTION_LABEL.get((atype or "").upper(), atype or "")

    def _action_tone_cls(atype) -> str:
        return _ACTION_TONE.get((atype or "").upper(), "neutral")

    # ── Insight type (rep_insights) ───────────────────────────────────
    _INSIGHT_TYPE_LABEL = {
        "persona":          "Persona",
        "buying_pattern":   "Hành vi mua",
        "decision_style":   "Phong cách QĐ",
        "life_event":       "Sự kiện",
        "relationship":     "Mối quan hệ",
        "advocate_signal":  "Advocate",
    }

    def _insight_type_label(itype) -> str:
        return _INSIGHT_TYPE_LABEL.get(itype or "", itype or "")

    # ── Day of week (0=Sun…6=Sat, matches DuckDB extract(dayofweek)) ──
    _DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    def _day_of_week_label(dow) -> str:
        try:
            return _DOW_LABELS[int(dow)]
        except (TypeError, ValueError, IndexError):
            return ""

    # ── Note type metadata ────────────────────────────────────────────
    _NOTE_TYPE_META = {
        "preference":   {"label": "preference",   "cls": "bdg--good",   "style": ""},
        "contact_pref": {"label": "liên lạc",     "cls": "bdg--accent", "style": "color:var(--purple-500,#7c3aed);border-color:color-mix(in srgb,var(--purple-500,#7c3aed) 30%,transparent);background:color-mix(in srgb,var(--purple-500,#7c3aed) 10%,transparent)"},
        "warning":      {"label": "⚠ cảnh báo",   "cls": "bdg--bad",   "style": ""},
        "outcome":      {"label": "kết quả",       "cls": "bdg",        "style": "color:var(--fg-2)"},
        "internal":     {"label": "nội bộ",        "cls": "bdg",        "style": "color:var(--fg-tertiary)"},
    }

    def _note_type_meta(note_type) -> object:
        return _NOTE_TYPE_META.get(note_type or "")

    env.filters["fmt_discount_pct"] = _fmt_discount_pct
    env.filters["margin_quality_cls"] = _margin_quality_cls
    env.filters["confidence_label"]    = _confidence_label
    env.filters["confidence_tone"]     = _confidence_tone
    env.filters["confidence_color"]    = _confidence_color
    env.filters["action_type_label"]   = _action_type_label
    env.filters["action_tone_cls"]     = _action_tone_cls
    env.filters["insight_type_label"]  = _insight_type_label
    env.filters["day_of_week_label"]   = _day_of_week_label
    env.filters["note_type_meta"]      = _note_type_meta

    return Jinja2Templates(env=env)

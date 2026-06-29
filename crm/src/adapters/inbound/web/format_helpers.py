"""Formatting helpers for the CRM web adapter (re-export shim).

The implementations live in domain-focused sub-modules; this module re-exports
them so existing imports (`from ...format_helpers import format_vnd, ...`) keep
working unchanged.

Ported from Go:
  crm/src/internal/adapters/inbound/web/format_helpers.go
  crm/src/internal/adapters/inbound/web/templates/helpers.go

  - fmt_currency: VND amounts, percentages, signed amounts
  - fmt_date:     date/datetime formatting, relative time, days since, date_key
  - fmt_badge:    badge CSS classes, status tones, verdicts, customer label
  - fmt_segment:  segment rule-definition extraction
  - fmt_text:     generic text helpers (truncate, join)

All re-exported functions are pure — safe to call from Jinja2 filters.
"""
from __future__ import annotations

from .fmt_badge import *  # noqa: F401,F403
from .fmt_currency import *  # noqa: F401,F403
from .fmt_date import *  # noqa: F401,F403
from .fmt_segment import *  # noqa: F401,F403
from .fmt_text import *  # noqa: F401,F403

from .fmt_badge import __all__ as _badge_all
from .fmt_currency import __all__ as _currency_all
from .fmt_date import __all__ as _date_all
from .fmt_segment import __all__ as _segment_all
from .fmt_text import __all__ as _text_all

__all__ = [
    *_currency_all,
    *_date_all,
    *_badge_all,
    *_segment_all,
    *_text_all,
]

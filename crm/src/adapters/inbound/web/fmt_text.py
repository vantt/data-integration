"""Generic text helpers for the CRM web adapter.

All functions are pure — safe to call from Jinja2 filters.
"""
from __future__ import annotations

__all__ = ["truncate_str", "join_nonempty"]


def truncate_str(s: str, n: int) -> str:
    """Truncate s to n runes, appending '…' if truncated."""
    if not s:
        return s
    runes = list(s)
    if len(runes) <= n:
        return s
    return "".join(runes[:n]) + "…"


def join_nonempty(items: list, sep: str = ", ") -> str:
    """Join non-empty/non-None items with sep."""
    return sep.join(str(x) for x in items if x)

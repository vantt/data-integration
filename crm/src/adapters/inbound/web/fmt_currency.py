"""VND currency and percentage formatting helpers for the CRM web adapter.

All functions are pure — safe to call from Jinja2 filters.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

__all__ = ["format_vnd", "fmt_vnd", "fmt_pct", "fmt_vnd_signed"]


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


# alias
fmt_vnd = format_vnd

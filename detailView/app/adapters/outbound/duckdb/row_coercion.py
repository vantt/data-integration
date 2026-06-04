"""Pure coercion helpers — raw DuckDB row values -> domain-friendly Python types.

Keeps duckdb-specific quirks (VARCHAR ids, VARCHAR birth_date, Decimal/float money) out of
the repositories and out of the domain. No duckdb import here on purpose: these are
plain functions over already-fetched values, so they stay trivially unit-testable.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def as_int(value: Any) -> int | None:
    """Coerce to int. fact_orders.order_id is VARCHAR in the serving layer."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_decimal(value: Any) -> Decimal | None:
    """Coerce money to Decimal. Some economics columns are DOUBLE/BIGINT, not DECIMAL."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    """Coerce a ratio/percentage to float (None-safe)."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_bool(value: Any) -> bool:
    """Coerce a BOOLEAN flag; None -> False (a missing flag means 'not present')."""
    return bool(value) if value is not None else False


def as_str(value: Any) -> str | None:
    """Pass strings through, stringify non-None scalars, keep None as None."""
    if value is None:
        return None
    return str(value)


def as_datetime(value: Any) -> datetime | None:
    """Pass DuckDB TIMESTAMPTZ (already a tz-aware datetime) through."""
    return value if isinstance(value, datetime) else None


def as_date(value: Any) -> date | None:
    """Coerce a DATE-or-VARCHAR (dim_customers.birth_date is VARCHAR) to date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[: len(fmt) + 4], fmt).date()
        except ValueError:
            continue
    return None


def digits_only(value: str | None) -> str:
    """Normalise a phone string to its digits for tolerant matching."""
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isdigit())

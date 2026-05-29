"""DuckDB read-only implementation of the SearchPort.

resolve_order: exact case-insensitive order_code OR exact order_id -> canonical order_code
(or None). order_code match has higher priority than order_id match.
resolve_customer: match on exact customer_id OR digits-normalised phone OR exact email;
returns up to 10 lightweight CustomerHit rows for the disambiguation dropdown.
"""
from __future__ import annotations

from app.domain.shared import CustomerHit

from . import row_coercion as rc
from .connection import read_only_connection
from .fetch_helpers import fetch_all_dicts, fetch_one_dict
from .sql_loader import load_sql


class DuckDbSearchAdapter:
    """Per-request connection search adapter. Satisfies SearchPort (runtime_checkable)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def resolve_order(self, query: str) -> str | None:
        """Return the canonical order_code for the query, else None.

        Matching priority (both exact / case-insensitive):
          1. order_code match  (e.g. user types '260529N88MBG3U')
          2. order_id match    (e.g. user types '1036830915')

        The query is passed three times to satisfy the three positional '?' placeholders
        in search_order.sql (CASE expression + WHERE clause pair).
        """
        if not query or not query.strip():
            return None
        q = query.strip()
        # Three '?' in search_order.sql: CASE WHEN clause, WHERE order_code, WHERE order_id.
        with read_only_connection(self._db_path) as conn:
            row = fetch_one_dict(conn, load_sql("search_order"), [q, q, q])
        return rc.as_str(row.get("order_code")) if row else None

    def resolve_customer(self, query: str) -> list[CustomerHit]:
        """Resolve a customer by id / phone / email. 0..10 hits."""
        if not query or not query.strip():
            return []
        term = query.strip()
        phone_digits = rc.digits_only(term)
        # Params order mirrors the placeholders in search_customer.sql:
        # id, phone-guard, phone-digits, email-guard, email.
        params = [term, phone_digits, phone_digits, term, term]
        with read_only_connection(self._db_path) as conn:
            rows = fetch_all_dicts(conn, load_sql("search_customer"), params)
        return [
            CustomerHit(
                customer_id=rc.as_str(r.get("customer_id")) or "",
                full_name=rc.as_str(r.get("full_name")),
                phone=rc.as_str(r.get("phone")),
                value_group=rc.as_str(r.get("value_group")),
            )
            for r in rows
        ]

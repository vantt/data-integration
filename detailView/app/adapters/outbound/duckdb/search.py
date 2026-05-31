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

        Matching priority (exact, case-insensitive):
          1. order_code  (rank 0)
          2. order_id    (rank 1)
          3. fulfillment_code / fulfillment_id / tracking_code via fact_fulfillments (rank 2)

        fact_fulfillments may not exist on older DBs; the SQL guards with a UNION ALL that
        produces zero rows when the view is absent — the INNER JOIN simply returns nothing
        rather than crashing. A missing view therefore produces no match, not an error.

        search_order.sql has 6 positional '?' placeholders:
          [0] CASE order_code, [1] WHERE order_code, [2] WHERE order_id,
          [3] WHERE fulfillment_code, [4] WHERE fulfillment_id, [5] WHERE tracking_code.
        """
        if not query or not query.strip():
            return None
        q = query.strip()
        # 6 params: CASE order_code, WHERE order_code, WHERE order_id,
        #           WHERE fulfillment_code, WHERE fulfillment_id, WHERE tracking_code.
        params = [q, q, q, q, q, q]
        try:
            with read_only_connection(self._db_path) as conn:
                row = fetch_one_dict(conn, load_sql("search_order"), params)
        except Exception:
            # Guard: if fact_fulfillments is structurally absent and DuckDB raises at parse
            # time (older schema without the view), fall back to order-only search.
            row = self._resolve_order_fallback(q)
        return rc.as_str(row.get("order_code")) if row else None

    def _resolve_order_fallback(self, q: str) -> dict | None:
        """Order-only search used when fact_fulfillments is unavailable."""
        _FALLBACK_SQL = (
            "SELECT order_code, "
            "CASE WHEN UPPER(order_code) = UPPER(?) THEN 0 ELSE 1 END AS match_rank "
            "FROM fact_orders "
            "WHERE UPPER(order_code) = UPPER(?) OR order_id = ? "
            "ORDER BY match_rank LIMIT 1"
        )
        try:
            with read_only_connection(self._db_path) as conn:
                return fetch_one_dict(conn, _FALLBACK_SQL, [q, q, q])
        except Exception:
            return None

    def resolve_customer(self, query: str) -> list[CustomerHit]:
        """Resolve a customer by id / customer_code (CUZN…) / phone / email. 0..10 hits."""
        if not query or not query.strip():
            return []
        term = query.strip()
        phone_digits = rc.digits_only(term)
        # Params order mirrors the placeholders in search_customer.sql:
        # id, customer_code, phone-guard, phone-digits, email-guard, email.
        params = [term, term, phone_digits, phone_digits, term, term]
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

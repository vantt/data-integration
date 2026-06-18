"""DuckDB read-only implementation of the OrderRepository port for CRM.

Reads the full single-order aggregate from olap.duckdb (serving layer).
Mirrors the Go DuckDB adapter (order_repo.go / order_repo_fetch.go) — same SQL,
same table names, same column aliases. SQL constants live in order_sql.py.

Resilience contract:
- olap.duckdb unavailable (open_olap returns None) → get_order_detail returns None
  so the HTTP layer can serve 503.
- Optional child collections degrade to [] on query error (never propagate 500).
- Core header query failure returns None (order not found or DB error).
"""
from __future__ import annotations

import logging

import duckdb

from crm.src.domain.entities.order import OrderDetail
from . import order_collection_mappers as cm
from . import order_mappers as om
from . import order_sql as sql
from .connection import open_olap

logger = logging.getLogger(__name__)


class DuckDBOrderRepository:
    """Per-request connection repository. Implements OrderRepository (duck-typed).

    Duck-typed against the OrderRepository protocol — no explicit base class.
    Add domain.ports.order_repository once the port is formalised.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_by_code(self, order_code: str) -> OrderDetail | None:
        return self.get_order_detail(order_code)

    def resolve_order_code(self, q: str) -> str | None:
        """Return canonical order_code for any identifier (code/id/fulfillment), or None."""
        if not q or not q.strip():
            return None
        q = q.strip()
        conn = open_olap(self._db_path)
        if conn is None:
            return None
        try:
            params = [q, q, q, q, q, q]
            try:
                rel = conn.execute(sql.RESOLVE_ORDER_SQL, params)
                row = rel.fetchone()
                return str(row[0]) if row and row[0] else None
            except Exception:
                # fact_fulfillments absent — fall back to order-only match
                rel = conn.execute(
                    "SELECT order_code FROM fact_orders "
                    "WHERE UPPER(order_code) = UPPER(?) OR order_id = ? LIMIT 1",
                    [q, q],
                )
                row = rel.fetchone()
                return str(row[0]) if row and row[0] else None
        except Exception:
            logger.warning("crm duckdb: resolve_order_code %r failed", q, exc_info=True)
            return None
        finally:
            conn.close()

    def find_customer_id_by_code(self, customer_code: str) -> str | None:
        """Return the Sapo numeric customer_id for a given customer_code, or None."""
        if not customer_code or not customer_code.strip():
            return None
        conn = open_olap(self._db_path)
        if conn is None:
            return None
        try:
            rel = conn.execute(
                "SELECT customer_id FROM main_marts.dim_customers WHERE customer_code = ? LIMIT 1",
                [customer_code.strip()],
            )
            row = rel.fetchone()
            return str(row[0]) if row and row[0] else None
        except Exception:
            logger.warning("find_customer_id_by_code %r failed", customer_code, exc_info=True)
            return None
        finally:
            conn.close()

    def get_order_detail(self, order_code: str) -> OrderDetail | None:
        """Full order aggregate for order_code (case-insensitive), or None.

        Returns None when:
        - order_code is blank
        - olap.duckdb is unavailable (caller returns 503)
        - order not found in fact_orders
        """
        if not order_code or not order_code.strip():
            return None

        code = order_code.strip()
        conn = open_olap(self._db_path)
        if conn is None:
            return None  # olap.duckdb unavailable — caller serves 503

        try:
            return self._fetch_aggregate(conn, code)
        finally:
            conn.close()

    # ── private helpers ───────────────────────────────────────────────────────

    def _fetch_aggregate(self, conn: duckdb.DuckDBPyConnection, code: str) -> OrderDetail | None:
        """Fetch all collections and assemble OrderDetail; None when not found."""
        header_row = self._fetch_one(conn, sql.HEADER_SQL, [code])
        if header_row is None:
            return None

        order_id = str(header_row.get("order_id") or "")
        canonical_code = str(header_row.get("order_code") or code)

        line_items = [cm.map_line_item(r)    for r in self._safe_fetch(conn, sql.LINE_ITEMS_SQL, [order_id],       "line_items")]
        costs      = [cm.map_cost_row(r)     for r in self._safe_fetch(conn, sql.COSTS_SQL,      [order_id],       "costs")]
        payments   = [cm.map_payment(r)      for r in self._safe_fetch(conn, sql.PAYMENTS_SQL,   [order_id],       "payments")]
        returns    = [cm.map_return_event(r) for r in self._safe_fetch(conn, sql.RETURNS_SQL,    [canonical_code], "returns")]
        shipments  = [cm.map_shipment(r)     for r in self._safe_fetch(conn, sql.SHIPMENTS_SQL,  [canonical_code], "shipments")]
        cogs_items = [cm.map_cogs_item(r)    for r in self._safe_fetch(conn, sql.COGS_ITEMS_SQL, [canonical_code], "cogs_items")]

        return OrderDetail(
            header=om.map_header(header_row),
            financial=om.map_financial(header_row),
            channel=om.map_channel(header_row),
            staff=om.map_staff(header_row),
            shipping=om.map_shipping(header_row),
            line_items=line_items,
            cost_ledger=costs,
            cogs_items=cogs_items,
            payments=payments,
            returns=returns,
            shipments=shipments,
            customer=om.map_customer(header_row),
        )

    @staticmethod
    def _fetch_one(conn: duckdb.DuckDBPyConnection, query: str, params: list) -> dict | None:
        """Run query and return the first row as a dict, or None if no rows."""
        try:
            rel = conn.execute(query, params)
            cols = [d[0] for d in rel.description]
            row = rel.fetchone()
            return dict(zip(cols, row)) if row is not None else None
        except Exception:  # noqa: BLE001
            logger.warning("crm duckdb: header query failed", exc_info=True)
            return None

    @staticmethod
    def _safe_fetch(
        conn: duckdb.DuckDBPyConnection,
        query: str,
        params: list,
        label: str,
    ) -> list[dict]:
        """Run query and return all rows as dicts; returns [] on any error."""
        try:
            rel = conn.execute(query, params)
            cols = [d[0] for d in rel.description]
            return [dict(zip(cols, row)) for row in rel.fetchall()]
        except Exception:  # noqa: BLE001 — degrade, don't crash
            logger.warning("crm duckdb: optional fetch '%s' failed — returning []", label, exc_info=True)
            return []

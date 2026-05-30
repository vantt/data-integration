"""DuckDB read-only implementation of the OrderRepository port.

Assembles the full single-order aggregate from the serving views:
header+economics+dims (one row), plus line items / costs / payments / returns
(many rows). US orders are detected via a fact_us_shipment_economics row and report
revenue from US fields rather than fact_orders.net_revenue (which is 0 for US).

Resilience: optional child collections (fact_fulfillments, fact_order_returns,
fact_order_costs, fact_payments) are wrapped in try/except so a missing or broken
view degrades gracefully (returns [] for that collection) rather than propagating a
500 to the user. Core queries (order header + economics) remain uncaught — a missing
core view surfaces as None (not-found), never as an unhandled exception reaching web.
"""
from __future__ import annotations

import logging

from app.domain.order import OrderDetail

from . import order_mappers as om
from .connection import read_only_connection
from .fetch_helpers import fetch_all_dicts, fetch_one_dict
from .sql_loader import load_sql

logger = logging.getLogger(__name__)


def _safe_fetch(conn, sql_name: str, params: list) -> list:
    """Fetch an optional collection; return [] and log on any exception."""
    try:
        return fetch_all_dicts(conn, load_sql(sql_name), params)
    except Exception:  # noqa: BLE001 — degrade, don't crash
        logger.warning("order_repository: optional fetch '%s' failed — returning []", sql_name, exc_info=True)
        return []


class DuckDbOrderRepository:
    """Per-request connection repository. Satisfies OrderRepository (runtime_checkable)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_by_code(self, order_code: str) -> OrderDetail | None:
        """Full order aggregate for ``order_code`` (case-insensitive), or None if absent."""
        if not order_code or not order_code.strip():
            return None
        code = order_code.strip()

        with read_only_connection(self._db_path) as conn:
            # CORE query — uncaught; missing view → None (not-found), not 500.
            header_row = fetch_one_dict(conn, load_sql("order_header"), [code])
            if header_row is None:
                return None

            # order_id is the join key for child collections (VARCHAR in serving layer).
            order_id = header_row.get("order_id")
            canonical_code = header_row.get("order_code") or code

            # OPTIONAL collections — degrade to [] on missing view / binder error.
            line_rows = _safe_fetch(conn, "order_line_items", [order_id])
            cost_rows = _safe_fetch(conn, "order_costs", [order_id])
            payment_rows = _safe_fetch(conn, "order_payments", [order_id])
            # Returns join on order_code (not order_id) — see researcher-01 §3.
            return_rows = _safe_fetch(conn, "order_returns", [canonical_code])
            # Shipments join on order_code (fact_fulfillments has no order_id FK).
            shipment_rows = _safe_fetch(conn, "order_shipments", [canonical_code])

        return OrderDetail(
            header=om.map_header(header_row),
            financial=om.map_financial(header_row),
            line_items=[om.map_line_item(r) for r in line_rows],
            cost_ledger=[om.map_cost_row(r) for r in cost_rows],
            payments=[om.map_payment(r) for r in payment_rows],
            returns=[om.map_return_event(r) for r in return_rows],
            shipments=[om.map_shipment(r) for r in shipment_rows],
            channel=om.map_channel(header_row),
            staff=om.map_staff(header_row),
            shipping=om.map_shipping(header_row),
            customer=om.map_customer_ref(header_row),
        )

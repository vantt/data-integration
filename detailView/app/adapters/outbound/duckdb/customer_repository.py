"""DuckDB read-only implementation of the CustomerRepository port.

Profile + behavior from dim_customers; value_metrics aggregated over fact_orders x
fact_order_economics; status_timeline from mart_customer_status_snapshot_monthly
(RETAIL-only — empty for non-RETAIL is expected); order_history newest-first, capped.

Resilience: optional child collections (mart_customer_status_snapshot_monthly,
customer_order_history, customer_value_metrics) are wrapped in try/except so a
missing or broken view degrades gracefully (returns [] / None) rather than
propagating a 500 to the user. Core profile query remains uncaught — a missing
dim_customers view surfaces as None (not-found), never as a 500.
"""
from __future__ import annotations

import logging

from app.domain.customer import CustomerDetail

from . import customer_mappers as cm
from .connection import read_only_connection
from .fetch_helpers import fetch_all_dicts, fetch_one_dict
from .sql_loader import load_sql

logger = logging.getLogger(__name__)

# Cap on order_history rows (a single customer view never needs the full lifetime list).
_ORDER_HISTORY_LIMIT = 200


def _safe_fetch(conn, sql_name: str, params: list) -> list:
    """Fetch an optional collection; return [] and log on any exception."""
    try:
        return fetch_all_dicts(conn, load_sql(sql_name), params)
    except Exception:  # noqa: BLE001 — degrade, don't crash
        logger.warning(
            "customer_repository: optional fetch '%s' failed — returning []",
            sql_name,
            exc_info=True,
        )
        return []


def _safe_fetch_one(conn, sql_name: str, params: list) -> dict | None:
    """Fetch an optional single row; return None and log on any exception."""
    try:
        return fetch_one_dict(conn, load_sql(sql_name), params)
    except Exception:  # noqa: BLE001 — degrade, don't crash
        logger.warning(
            "customer_repository: optional fetch_one '%s' failed — returning None",
            sql_name,
            exc_info=True,
        )
        return None


class DuckDbCustomerRepository:
    """Per-request connection repository. Satisfies CustomerRepository (runtime_checkable)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_by_id(self, customer_id: str) -> CustomerDetail | None:
        """Full customer aggregate for ``customer_id``, or None if absent."""
        if not customer_id or not customer_id.strip():
            return None
        cid = customer_id.strip()

        with read_only_connection(self._db_path) as conn:
            # CORE query — uncaught; missing view → None (not-found), not 500.
            profile_row = fetch_one_dict(conn, load_sql("customer_profile"), [cid])
            if profile_row is None:
                return None

            customer_key = profile_row.get("customer_key")

            # OPTIONAL collections — degrade gracefully on missing view / binder error.
            agg_row = _safe_fetch_one(conn, "customer_value_metrics", [customer_key])
            timeline_rows = _safe_fetch(conn, "customer_status_timeline", [customer_key])
            history_rows = _safe_fetch(
                conn, "customer_order_history", [customer_key, _ORDER_HISTORY_LIMIT]
            )

        return CustomerDetail(
            profile=cm.map_profile(profile_row),
            value_metrics=cm.map_value_metrics(profile_row, agg_row),
            behavior=cm.map_behavior(profile_row),
            status_timeline=[cm.map_status_snapshot(r) for r in timeline_rows],
            order_history=[cm.map_order_summary(r) for r in history_rows],
        )

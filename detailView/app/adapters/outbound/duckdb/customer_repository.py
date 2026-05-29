"""DuckDB read-only implementation of the CustomerRepository port.

Profile + behavior from dim_customers; value_metrics aggregated over fact_orders x
fact_order_economics; status_timeline from mart_customer_status_snapshot_monthly
(RETAIL-only — empty for non-RETAIL is expected); order_history newest-first, capped.
"""
from __future__ import annotations

from app.domain.customer import CustomerDetail

from . import customer_mappers as cm
from .connection import read_only_connection
from .fetch_helpers import fetch_all_dicts, fetch_one_dict
from .sql_loader import load_sql

# Cap on order_history rows (a single customer view never needs the full lifetime list).
_ORDER_HISTORY_LIMIT = 200


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
            profile_row = fetch_one_dict(conn, load_sql("customer_profile"), [cid])
            if profile_row is None:
                return None

            customer_key = profile_row.get("customer_key")
            agg_row = fetch_one_dict(
                conn, load_sql("customer_value_metrics"), [customer_key]
            )
            timeline_rows = fetch_all_dicts(
                conn, load_sql("customer_status_timeline"), [customer_key]
            )
            history_rows = fetch_all_dicts(
                conn,
                load_sql("customer_order_history"),
                [customer_key, _ORDER_HISTORY_LIMIT],
            )

        return CustomerDetail(
            profile=cm.map_profile(profile_row),
            value_metrics=cm.map_value_metrics(profile_row, agg_row),
            behavior=cm.map_behavior(profile_row),
            status_timeline=[cm.map_status_snapshot(r) for r in timeline_rows],
            order_history=[cm.map_order_summary(r) for r in history_rows],
        )

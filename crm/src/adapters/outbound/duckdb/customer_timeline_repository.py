"""DuckDB read-only repository for customer status timeline.

Reads from mart_customer_status_snapshot_monthly (RETAIL-only mart).
Degrades gracefully when the mart is missing — returns [] rather than raising.
"""
from __future__ import annotations

import logging

from domain.entities.cache_insight import StatusSnapshot
from . import customer_timeline_sql as sql
from .connection import open_olap

logger = logging.getLogger(__name__)


class CustomerTimelineRepository:
    """Read-only access to mart_customer_status_snapshot_monthly."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_by_customer_id(self, customer_id: int) -> list[StatusSnapshot]:
        """Return up to 24 monthly snapshots for customer_id, oldest-first.

        Uses dim_customers join to resolve customer_key. Returns [] when
        the mart is absent or the customer has no snapshot rows.
        """
        if not customer_id:
            return []
        conn = open_olap(self._db_path)
        if conn is None:
            return []
        try:
            return self._fetch(conn, sql.TIMELINE_BY_CUSTOMER_ID, [customer_id])
        finally:
            conn.close()

    def get_by_customer_key(self, customer_key: str) -> list[StatusSnapshot]:
        """Return up to 24 monthly snapshots for customer_key, oldest-first."""
        if not customer_key:
            return []
        conn = open_olap(self._db_path)
        if conn is None:
            return []
        try:
            return self._fetch(conn, sql.TIMELINE_BY_CUSTOMER_KEY, [customer_key])
        finally:
            conn.close()

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fetch(conn, query: str, params: list) -> list[StatusSnapshot]:
        try:
            rel = conn.execute(query, params)
            cols = [d[0] for d in rel.description]
            rows = [dict(zip(cols, r)) for r in rel.fetchall()]
        except Exception:  # noqa: BLE001 — mart may not exist yet
            logger.warning(
                "customer_timeline_repository: fetch failed — returning []",
                exc_info=True,
            )
            return []
        return [
            StatusSnapshot(
                snapshot_month=str(r.get("snapshot_month") or ""),
                status=str(r.get("status") or ""),
                days_since_last_order=r.get("days_since_last_order"),
                value_group=str(r.get("value_group") or ""),
                is_new=bool(r.get("is_new")),
            )
            for r in rows
        ]

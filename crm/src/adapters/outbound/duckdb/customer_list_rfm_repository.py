"""DuckDB batch Recency / Frequency / customer_type for the S02 customer list.

One round-trip per page load: fetches RFM metrics for up to 30 customer_ids at once.
Degrades gracefully — returns {} when olap.duckdb is unavailable.
"""
from __future__ import annotations

import logging

from . import customer_list_rfm_sql as sql
from .connection import open_olap

logger = logging.getLogger(__name__)


class CustomerListRFMRepository:
    """Read-only batch RFM lookup keyed by Sapo customer_id."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_rfm_for_customer_ids(self, customer_ids: list[int]) -> dict[int, dict]:
        """Return {customer_id: {customer_type, last_order_date, order_count}}.

        Returns {} on any error or when olap.duckdb is unavailable.
        """
        if not customer_ids:
            return {}
        conn = open_olap(self._db_path)
        if conn is None:
            return {}
        try:
            str_ids = [str(cid) for cid in customer_ids]
            rel = conn.execute(sql.BATCH_RFM, [str_ids])
            cols = [d[0] for d in rel.description]
            rows = [dict(zip(cols, r)) for r in rel.fetchall()]
        except Exception:
            logger.warning("customer_list_rfm: batch fetch failed", exc_info=True)
            return {}
        finally:
            conn.close()

        result: dict[int, dict] = {}
        for r in rows:
            try:
                cid = int(r["customer_id"])
            except (TypeError, ValueError):
                continue
            result[cid] = {
                "customer_type": str(r.get("customer_type") or ""),
                "last_order_date": str(r.get("last_order_date") or ""),
                "order_count": int(r.get("order_count") or 0),
            }
        return result

"""DuckDB read-only repository for customer order history with GP/margin/seller.

Reads fact_orders × fact_order_economics × dims from olap.duckdb.
Degrades gracefully when olap.duckdb is unavailable or mart is missing.
"""
from __future__ import annotations

import logging

from crm.src.domain.entities.cache_insight import CustomerOrderRow
from . import customer_orders_sql as sql
from .connection import open_olap

logger = logging.getLogger(__name__)


class CustomerOrdersRepository:
    """Read-only access to customer order history from olap.duckdb."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_by_customer_id(self, customer_id: int) -> list[CustomerOrderRow]:
        """Return up to 50 orders for customer_id, newest first.

        Returns [] when olap.duckdb is unavailable or no rows exist.
        """
        if not customer_id:
            return []
        conn = open_olap(self._db_path)
        if conn is None:
            return []
        try:
            rel = conn.execute(sql.ORDERS_BY_CUSTOMER_ID, [customer_id])
            cols = [d[0] for d in rel.description]
            rows = [dict(zip(cols, r)) for r in rel.fetchall()]
        except Exception:  # noqa: BLE001
            logger.warning(
                "customer_orders_repository: fetch for customer_id=%s failed — returning []",
                customer_id,
                exc_info=True,
            )
            return []
        finally:
            conn.close()

        return [
            CustomerOrderRow(
                order_code=str(r.get("order_code") or ""),
                created_at=str(r.get("created_at") or ""),
                status=str(r.get("status") or ""),
                channel_name=str(r.get("channel_name") or ""),
                seller_name=str(r.get("seller_name") or ""),
                total_collected=float(r.get("total_collected") or 0.0),
                gross_profit=_opt_float(r.get("gross_profit")),
                gross_margin_pct=_opt_float(r.get("gross_margin_pct")),
                payment_label=str(r.get("payment_label") or ""),
                has_return=bool(r.get("has_return")),
            )
            for r in rows
        ]


def _opt_float(v) -> float | None:
    """Return float or None for nullable numeric columns."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

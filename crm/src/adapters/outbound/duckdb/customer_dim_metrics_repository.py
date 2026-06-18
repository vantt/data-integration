"""DuckDB read-only repository for customer behavior segments + aggregated value metrics.

Queries dim_customers for lifecycle/affinity/payment segments, then
fact_orders × fact_order_economics for profitability and returns KPIs.
Degrades gracefully — returns None rather than raising on any error.
"""
from __future__ import annotations

import logging
from typing import Optional

from crm.src.domain.entities.cache_insight import CustomerDimMetrics
from . import customer_dim_metrics_sql as sql
from .connection import open_olap

logger = logging.getLogger(__name__)


class CustomerDimMetricsRepository:
    """Read-only access to dim_customers segments + aggregated order economics."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_by_customer_id(self, customer_id: int) -> Optional[CustomerDimMetrics]:
        """Fetch behavior segments + value metrics for a Sapo customer_id.

        Two-step: dim_customers → customer_key, then fact_orders × economics aggregate.
        Returns None when the customer has no dim row or on any DuckDB error.
        """
        if not customer_id:
            return None
        try:
            return self._fetch(customer_id)
        except Exception:  # noqa: BLE001 — any failure is non-fatal
            logger.warning(
                "customer_dim_metrics_repository: fetch failed for customer_id=%d",
                customer_id,
                exc_info=True,
            )
            return None

    # ── private ───────────────────────────────────────────────────────────────

    def _fetch(self, customer_id: int) -> Optional[CustomerDimMetrics]:
        conn = open_olap(self._db_path)
        if conn is None:
            return None
        try:
            # Step 1: resolve dim row — segments + customer_key
            rel = conn.execute(sql.DIM_BY_CUSTOMER_ID, [customer_id])
            cols = [d[0] for d in rel.description]
            row = rel.fetchone()
            if row is None:
                return None
            dim = dict(zip(cols, row))
            customer_key: str = str(dim.get("customer_key") or "")
            if not customer_key:
                return None

            # Step 2: aggregate value metrics
            rel2 = conn.execute(sql.VALUE_METRICS_BY_CUSTOMER_KEY, [customer_key])
            cols2 = [d[0] for d in rel2.description]
            row2 = rel2.fetchone()
            vm = dict(zip(cols2, row2)) if row2 else {}

            # cohort_month from first_order_date (YYYY-MM-DD → YYYY-MM)
            first_order_date = str(dim.get("first_order_date") or "")
            cohort_month = first_order_date[:7] if first_order_date else ""

            return CustomerDimMetrics(
                customer_key=customer_key,
                lifecycle_stage=str(dim.get("lifecycle_stage") or ""),
                product_affinity=str(dim.get("product_affinity") or ""),
                payment_behavior=str(dim.get("payment_behavior") or ""),
                geo_region=str(dim.get("geo_region") or ""),
                customer_type=str(dim.get("customer_type") or ""),
                cohort_month=cohort_month,
                total_gross_profit=_opt_float(vm.get("total_gross_profit")),
                total_cogs=_opt_float(vm.get("total_cogs")),
                avg_gross_margin_pct=_opt_float(vm.get("avg_gross_margin_pct")),
                cogs_order_count=_opt_int(vm.get("cogs_order_count")),
                order_count=_opt_int(vm.get("order_count")),
                total_return_amount=_opt_float(vm.get("total_return_amount")),
                return_count=_opt_int(vm.get("return_count")),
            )
        finally:
            conn.close()


# ── helpers ───────────────────────────────────────────────────────────────────

def _opt_float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _opt_int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None

"""Customer repository mapping tests against the seeded temp DuckDB."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.adapters.outbound.duckdb.customer_repository import DuckDbCustomerRepository


def test_get_by_id_unknown_returns_none(seeded_db_path: str) -> None:
    repo = DuckDbCustomerRepository(seeded_db_path)
    assert repo.get_by_id("NOPE") is None


def test_retail_customer_full_aggregate(seeded_db_path: str) -> None:
    repo = DuckDbCustomerRepository(seeded_db_path)
    detail = repo.get_by_id("CUST-1")
    assert detail is not None

    # Profile incl. VARCHAR dob coerced to date.
    assert detail.profile.full_name == "Nguyen Van A"
    assert detail.profile.dob == date(1990, 5, 15)
    assert detail.is_retail is True
    assert detail.timeline_available is True

    # Value metrics aggregated over the 2 orders (ORD-NORMAL + ORD-NOCOGS).
    vm = detail.value_metrics
    assert vm.total_orders_count == 2
    assert vm.lifetime_value == Decimal("1760000")  # 1,100,000 + 660,000
    assert vm.total_gross_profit == Decimal("1200000")  # 600,000 + 600,000
    assert vm.total_cogs == Decimal("400000")  # only ORD-NORMAL has COGS
    assert vm.cogs_order_count == 1  # coverage caveat: 1 of 2 orders
    assert vm.return_count == 1

    # Behavior derived from dim_customers.
    assert detail.behavior.lifecycle_stage == "LIFECYCLE_ACTIVE"
    assert detail.behavior.frequency == 2

    # RETAIL status timeline present.
    assert len(detail.status_timeline) == 1
    assert detail.status_timeline[0].status == "ACTIVE"

    # Order history newest-first (ORD-NOCOGS 2026-03 before ORD-NORMAL 2026-01).
    codes = [o.order_code for o in detail.order_history]
    assert codes == ["ORD-NOCOGS", "ORD-NORMAL"]
    assert detail.order_history[1].payment_label == "COD"
    assert detail.order_history[1].has_return is True


def test_non_retail_customer_has_empty_timeline(seeded_db_path: str) -> None:
    repo = DuckDbCustomerRepository(seeded_db_path)
    detail = repo.get_by_id("CUST-2")
    assert detail is not None
    assert detail.is_retail is False
    assert detail.timeline_available is False
    assert detail.status_timeline == []  # RETAIL-only mart -> empty is fine
    assert [o.order_code for o in detail.order_history] == ["ORD-US"]

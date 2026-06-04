"""Search adapter tests for shipment identifier resolution via fact_fulfillments.

Covers:
- resolve_order(fulfillment_code)  → correct order_code
- resolve_order(fulfillment_id)    → correct order_code
- resolve_order(tracking_code)     → correct order_code
- order_code / order_id priority preserved (rank < 2 wins over shipment rank 2)
- junk query → None
- existing order_code and order_id tests still pass (regression)
"""
from __future__ import annotations

import pytest

from app.adapters.outbound.duckdb.search import DuckDbSearchAdapter


# ---------------------------------------------------------------------------
# Shipment identifier resolution
# ---------------------------------------------------------------------------

def test_resolve_order_by_fulfillment_code(seeded_db_path: str) -> None:
    """fulfillment_code 'SHIP-A' must resolve to its parent order_code."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("SHIP-A") == "ORD-NORMAL"


def test_resolve_order_by_fulfillment_code_case_insensitive(seeded_db_path: str) -> None:
    """fulfillment_code match must be case-insensitive."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("ship-a") == "ORD-NORMAL"
    assert adapter.resolve_order("SHIP-A") == "ORD-NORMAL"


def test_resolve_order_by_fulfillment_id(seeded_db_path: str) -> None:
    """fulfillment_id 'FF-001' must resolve to the correct order_code."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("FF-001") == "ORD-NORMAL"


def test_resolve_order_by_tracking_code(seeded_db_path: str) -> None:
    """tracking_code must resolve to the parent order_code."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("GHTK-TRACK-001") == "ORD-NORMAL"
    # Second shipment of the same order.
    assert adapter.resolve_order("GHTK-TRACK-002") == "ORD-NORMAL"


def test_resolve_order_by_tracking_code_case_insensitive(seeded_db_path: str) -> None:
    """tracking_code match must be case-insensitive."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("ghtk-track-001") == "ORD-NORMAL"


# ---------------------------------------------------------------------------
# Priority: order_code (rank 0) and order_id (rank 1) still win over shipment (rank 2)
# ---------------------------------------------------------------------------

def test_order_code_priority_over_shipment(seeded_db_path: str) -> None:
    """A query matching order_code must return rank-0 result, not any shipment match."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("ORD-NORMAL") == "ORD-NORMAL"


def test_order_id_priority_over_shipment(seeded_db_path: str) -> None:
    """order_id '9991' → 'CODE-ALPHA' must still work alongside shipment search."""
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("9991") == "CODE-ALPHA"


# ---------------------------------------------------------------------------
# Regression: existing order_code / order_id tests still pass
# ---------------------------------------------------------------------------

def test_existing_order_code_search_unaffected(seeded_db_path: str) -> None:
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("ord-normal") == "ORD-NORMAL"
    assert adapter.resolve_order("ORD-US") == "ORD-US"
    assert adapter.resolve_order("code-alpha") == "CODE-ALPHA"


def test_junk_returns_none(seeded_db_path: str) -> None:
    adapter = DuckDbSearchAdapter(seeded_db_path)
    assert adapter.resolve_order("DOES-NOT-EXIST") is None
    assert adapter.resolve_order("") is None
    assert adapter.resolve_order("   ") is None


# ---------------------------------------------------------------------------
# Guard: missing fact_fulfillments view must not crash search
# ---------------------------------------------------------------------------

def test_missing_fulfillments_view_does_not_crash(tmp_path: pytest.TempPathFactory) -> None:
    """Search must fall back gracefully when fact_fulfillments does not exist.

    Creates a minimal DB with only fact_orders (no fact_fulfillments) and verifies
    that resolve_order still returns a result for order_code and None for junk.
    """
    import duckdb

    db_path = str(tmp_path / "no_fulfillments.duckdb")  # type: ignore[operator]
    con = duckdb.connect(db_path)
    try:
        con.execute(
            "CREATE TABLE fact_orders ("
            "order_id VARCHAR, order_code VARCHAR, "
            "status VARCHAR, payment_status VARCHAR, fulfillment_status VARCHAR, "
            "gross_revenue DECIMAL(18,2), discount_amount DECIMAL(18,2), "
            "net_revenue DECIMAL(18,2), vat_amount DECIMAL(18,2), "
            "total_collected DECIMAL(18,2), first_shipped_at TIMESTAMPTZ, "
            "time_to_complete_hours BIGINT, ordered_at TIMESTAMPTZ, "
            "updated_at TIMESTAMPTZ)"
        )
        con.execute(
            "INSERT INTO fact_orders (order_id, order_code) VALUES ('42', 'FALLBACK-ORDER')"
        )
    finally:
        con.close()

    adapter = DuckDbSearchAdapter(db_path)
    # order_code must still resolve even without fact_fulfillments
    result = adapter.resolve_order("FALLBACK-ORDER")
    assert result == "FALLBACK-ORDER"
    # junk must still return None
    assert adapter.resolve_order("NONEXISTENT") is None

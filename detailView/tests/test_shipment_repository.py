"""Shipment repository tests — verifies fact_fulfillments rows surface in OrderDetail."""
from __future__ import annotations

from decimal import Decimal

from app.adapters.outbound.duckdb.order_repository import DuckDbOrderRepository


def test_order_has_two_shipments(seeded_db_path: str) -> None:
    """ORD-NORMAL has exactly 2 seeded shipment legs."""
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NORMAL")
    assert detail is not None
    assert len(detail.shipments) == 2


def test_shipments_ordered_shipped_at_nulls_last(seeded_db_path: str) -> None:
    """SHIP-A (has shipped_at) must come before SHIP-B (shipped_at IS NULL)."""
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NORMAL")
    assert detail is not None
    codes = [s.fulfillment_code for s in detail.shipments]
    assert codes == ["SHIP-A", "SHIP-B"], f"Unexpected order: {codes}"


def test_shipment_fields_mapped_correctly(seeded_db_path: str) -> None:
    """Verify every field on the delivered leg (SHIP-A) is correctly coerced."""
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NORMAL")
    assert detail is not None

    delivered = next(s for s in detail.shipments if s.fulfillment_code == "SHIP-A")
    assert delivered.fulfillment_id == "FF-001"
    assert delivered.tracking_code == "GHTK-TRACK-001"
    assert delivered.carrier_id == "GHTK"
    assert delivered.shipping_service == "standard"
    assert delivered.status == "DELIVERED"
    assert delivered.cod_amount == Decimal("1100000")
    assert delivered.shipped_at is not None
    assert delivered.created_at is not None


def test_shipment_null_fields_coerced_to_none(seeded_db_path: str) -> None:
    """SHIP-B: cod_amount and shipped_at are NULL in seed — must map to None."""
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NORMAL")
    assert detail is not None

    shipping = next(s for s in detail.shipments if s.fulfillment_code == "SHIP-B")
    assert shipping.cod_amount is None
    assert shipping.shipped_at is None
    assert shipping.status == "SHIPPING"


def test_order_without_shipments_returns_empty_list(seeded_db_path: str) -> None:
    """ORD-US has no seeded fulfillments — shipments list must be empty, not None."""
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-US")
    assert detail is not None
    assert detail.shipments == []


def test_shipment_status_tone_delivered(seeded_db_path: str) -> None:
    """DELIVERED status must yield Tone.GOOD via the domain helper."""
    from app.domain.shared import Tone

    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NORMAL")
    assert detail is not None

    delivered = next(s for s in detail.shipments if s.fulfillment_code == "SHIP-A")
    assert delivered.status_tone() == Tone.GOOD


def test_shipment_status_tone_shipping(seeded_db_path: str) -> None:
    """SHIPPING status must yield Tone.WARN."""
    from app.domain.shared import Tone

    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NORMAL")
    assert detail is not None

    in_transit = next(s for s in detail.shipments if s.fulfillment_code == "SHIP-B")
    assert in_transit.status_tone() == Tone.WARN

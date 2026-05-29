"""Order repository mapping tests against the seeded temp DuckDB."""
from __future__ import annotations

from decimal import Decimal

from app.adapters.outbound.duckdb.order_repository import DuckDbOrderRepository


def test_get_by_code_returns_none_for_unknown(seeded_db_path: str) -> None:
    repo = DuckDbOrderRepository(seeded_db_path)
    assert repo.get_by_code("DOES-NOT-EXIST") is None


def test_get_by_code_is_case_insensitive(seeded_db_path: str) -> None:
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ord-normal")
    assert detail is not None
    assert detail.header.order_code == "ORD-NORMAL"
    assert detail.header.order_id == 1001  # VARCHAR in DB -> coerced to int


def test_normal_order_full_aggregate(seeded_db_path: str) -> None:
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NORMAL")
    assert detail is not None

    fin = detail.financial
    assert fin.has_cogs is True
    assert fin.cogs_amount == Decimal("400000")
    assert fin.net_revenue == Decimal("1000000")
    assert fin.is_us is False
    # Domestic effective revenue = total_collected.
    assert fin.effective_revenue == Decimal("1100000")
    assert fin.margin_is_verified is True

    # 2 line items, ordered by item_id.
    assert [li.sku for li in detail.line_items] == ["SKU-001", "SKU-002"]
    assert detail.line_items[0].quantity == 2
    assert detail.line_items[0].us_price_incl_vat is None

    # Cost ledger, payments.
    assert {c.cost_category for c in detail.cost_ledger} == {"COGS", "PLATFORM_FEE"}
    assert len(detail.payments) == 1
    assert detail.payments[0].payment_method_name == "COD"

    # Returns join by order_code.
    assert fin.has_returns is True
    assert len(detail.returns) == 1
    assert detail.returns[0].refund_amount == Decimal("150000")
    assert detail.returns[0].return_date is not None

    # Channel / staff / shipping / customer ref enrichment.
    assert detail.channel.channel_name == "Shopee Official"
    assert detail.channel.promotion_code == "SALE10"
    assert detail.staff.seller_name == "Alice Seller"
    assert detail.staff.team_name == "Team North"
    assert detail.shipping.province == "Ho Chi Minh"
    assert detail.customer.customer_id == "CUST-1"


def test_us_order_uses_us_revenue(seeded_db_path: str) -> None:
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-US")
    assert detail is not None
    fin = detail.financial

    assert fin.is_us is True
    assert fin.net_revenue == Decimal("0")  # fact_orders records US as 0
    assert fin.us_revenue_incl_vat == Decimal("4950000.0000")
    # effective_revenue swaps to US incl-VAT for US orders.
    assert fin.effective_revenue == Decimal("4950000.0000")
    assert fin.us_line_item_count == 2
    assert fin.has_unpriced_sku is True
    assert fin.unpriced_sku_count == 1


def test_no_cogs_order_flags_false(seeded_db_path: str) -> None:
    repo = DuckDbOrderRepository(seeded_db_path)
    detail = repo.get_by_code("ORD-NOCOGS")
    assert detail is not None
    assert detail.financial.has_cogs is False
    assert detail.financial.margin_is_verified is False
    assert detail.financial.cogs_amount is None
    assert detail.returns == []
